import json
import math
import urllib.parse
from collections import Counter
import boto3

s3 = boto3.client("s3")

# Limiar padrão para o Teste KS e Qui-Quadrado
KS_THRESHOLD = 0.20
CHI2_THRESHOLD = 0.20


# ============================================================
# PARSER CSV INTELIGENTE (SUPORTA NÚMEROS E TEXTOS)
# ============================================================


def parse_csv_typed(csv_text):
    """
    Lê o CSV e identifica automaticamente o tipo de cada coluna.
    Retorna dois dicionários: um para colunas numéricas e outro para texto.
    """
    lines = csv_text.splitlines()

    if not lines:
        return {}, {}

    headers = [col.strip() for col in lines[0].split(",")]
    
    numeric_cols = {header: [] for header in headers}
    text_cols = {header: [] for header in headers}

    for line in lines[1:]:
        if not line.strip():
            continue

        cols = line.split(",")

        if len(cols) != len(headers):
            continue

        for header, val in zip(headers, cols):
            val_str = val.strip()
            try:
                # Tenta converter para float (coluna numérica)
                numeric_cols[header].append(float(val_str))
            except ValueError:
                # Se falhar, armazena como texto (coluna categórica)
                text_cols[header].append(val_str)

    # Filtra mantendo apenas colunas que realmente possuem dados no seu respectivo tipo
    final_numeric = {k: v for k, v in numeric_cols.items() if len(v) > 0}
    final_text = {k: v for k, v in text_cols.items() if len(v) > 0 and k not in final_numeric}

    return final_numeric, final_text


# ============================================================
# TESTE KOLMOGOROV-SMIRNOV (PARA VARIÁVEIS NUMÉRICAS)
# ============================================================


def simple_ks_test(data1, data2):
    n1, n2 = len(data1), len(data2)

    if n1 == 0 or n2 == 0:
        return 0.0

    d1, d2 = sorted(data1), sorted(data2)
    values = sorted(list(set(data1 + data2)))

    i1, i2 = 0, 0
    max_d = 0.0

    for v in values:
        while i1 < n1 and d1[i1] <= v:
            i1 += 1
        while i2 < n2 and d2[i2] <= v:
            i2 += 1

        f1 = i1 / n1
        f2 = i2 / n2
        d = abs(f1 - f2)

        if d > max_d:
            max_d = d

    return max_d


# ============================================================
# DISTÂNCIA DE PROPORÇÃO / CHI-SQUARE SIMPLIFICADO (PARA TEXTO)
# ============================================================


def categorical_drift_test(data1, data2):
    """
    Calcula a maior variação percentual na frequência das categorias
    entre o conjunto de baseline e o de inferência.
    """
    n1, n2 = len(data1), len(data2)
    if n1 == 0 or n2 == 0:
        return 0.0

    count1 = Counter(data1)
    count2 = Counter(data2)

    all_categories = set(count1.keys()).union(set(count2.keys()))
    max_diff = 0.0

    for cat in all_categories:
        prop1 = count1[cat] / n1
        prop2 = count2[cat] / n2
        diff = abs(prop1 - prop2)
        if diff > max_diff:
            max_diff = diff

    return max_diff


# ============================================================
# MÉTRICAS DE MODEL DRIFT
# ============================================================


def calculate_regression_metrics(y_true, y_pred):
    n = len(y_true)
    if n == 0:
        return {}

    mae = sum(abs(a - b) for a, b in zip(y_true, y_pred)) / n
    mse = sum((a - b) ** 2 for a, b in zip(y_true, y_pred)) / n
    rmse = math.sqrt(mse)

    return {"mae": round(mae, 4), "rmse": round(rmse, 4)}


# ============================================================
# AUXILIARES S3
# ============================================================


def read_s3_text(bucket, key):
    obj = s3.get_object(Bucket=bucket, Key=key)
    return obj["Body"].read().decode("utf-8")


def file_exists(bucket, key):
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except Exception:
        return False


def save_s3_json(bucket, key, payload):
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(payload, indent=2),
        ContentType="application/json",
    )


# ============================================================
# LAMBDA HANDLER
# ============================================================


def lambda_handler(event, context):
    record = event["Records"][0]
    bucket = record["s3"]["bucket"]["name"]
    key = urllib.parse.unquote_plus(
        record["s3"]["object"]["key"], encoding="utf-8"
    )

    print("=" * 60)
    print("MONITORAMENTO DE DRIFT (SUPORTE A DADOS MISTOS)")
    print("=" * 60)

    parts = key.split("/")

    if len(parts) < 3 or parts[0] != "inference":
        return {"statusCode": 200, "body": "Ignorado"}

    endpoint_id = parts[1]
    filename = parts[-1]
    data_id = filename.replace(".csv", "")

    baseline_key = f"baseline/{endpoint_id}.csv"
    ground_truth_key = f"ground_truth/{endpoint_id}/{filename}"
    data_drift_report_key = f"reports/{endpoint_id}/data_drift/{data_id}.json"
    model_drift_report_key = f"reports/{endpoint_id}/model_drift/{data_id}.json"

    # Carregar Inferência
    try:
        inference_text = read_s3_text(bucket, key)
        inf_numeric, inf_text = parse_csv_typed(inference_text)
    except Exception as e:
        print(f"Erro ao ler inferência: {str(e)}")
        return {"statusCode": 500, "body": "Erro ao processar CSV"}

    # ============================================================
    # DATA DRIFT (NUMÉRICO + CATEGÓRICO)
    # ============================================================

    if file_exists(bucket, baseline_key):
        baseline_text = read_s3_text(bucket, baseline_key)
        base_numeric, base_text = parse_csv_typed(baseline_text)

        ks_statistics = {}
        drift_detected = False

        # 1. Avalia colunas numéricas via KS Test
        for col_name, inf_vals in inf_numeric.items():
            if col_name in base_numeric:
                base_vals = base_numeric[col_name]
                ks_stat = simple_ks_test(base_vals, inf_vals)
                ks_statistics[col_name] = round(ks_stat, 4)

                if ks_stat > KS_THRESHOLD:
                    drift_detected = True

        # 2. Avalia colunas não numéricas (texto/categóricas) via Proporção
        for col_name, inf_vals in inf_text.items():
            if col_name in base_text:
                base_vals = base_text[col_name]
                cat_stat = categorical_drift_test(base_vals, inf_vals)
                ks_statistics[col_name] = round(cat_stat, 4)

                if cat_stat > CHI2_THRESHOLD:
                    drift_detected = True

        data_drift_payload = {
            "endpoint": endpoint_id,
            "drift_detected": drift_detected,
            "ks_statistics": ks_statistics,
        }

        save_s3_json(bucket, data_drift_report_key, data_drift_payload)
        print(f"Relatório Data Drift gerado com sucesso.")

    # ============================================================
    # MODEL DRIFT
    # ============================================================

    if file_exists(bucket, ground_truth_key):
        ground_truth_text = read_s3_text(bucket, ground_truth_key)
        gt_numeric, _ = parse_csv_typed(ground_truth_text)

        target_col = None
        for col in gt_numeric.keys():
            if col in inf_numeric:
                target_col = col
                break

        if target_col:
            y_pred = inf_numeric[target_col]
            y_true = gt_numeric[target_col]

            metrics = calculate_regression_metrics(y_true, y_pred)

            model_drift_payload = {
                "endpoint": endpoint_id,
                "metrics": metrics,
                "model_drift": False,
            }

            save_s3_json(bucket, model_drift_report_key, model_drift_payload)
            print(f"Relatório Model Drift gerado com sucesso.")

    return {"statusCode": 200, "body": json.dumps({"status": "Sucesso"})}
