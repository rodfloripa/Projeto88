import json
import math
import urllib.parse
import boto3

s3 = boto3.client("s3")

# Limiar padrão para o Teste Kolmogorov-Smirnov
KS_THRESHOLD = 0.20


# ============================================================
# PARSER CSV DINÂMICO
# ============================================================


def parse_csv_all_columns(csv_text):
    """
    Lê o CSV em formato texto e retorna um dicionário com os nomes
    das colunas e suas respectivas listas de valores float.
    Exemplo: {'temperatura': [23.1, 24.0], 'umidade': [60.0, 58.5]}
    """
    lines = csv_text.splitlines()

    if not lines:
        return {}

    headers = [col.strip() for col in lines[0].split(",")]
    columns_data = {header: [] for header in headers}

    for line in lines[1:]:
        if not line.strip():
            continue

        cols = line.split(",")

        if len(cols) != len(headers):
            continue

        for header, val in zip(headers, cols):
            try:
                columns_data[header].append(float(val.strip()))
            except ValueError:
                pass

    return columns_data


# ============================================================
# TESTE KOLMOGOROV-SMIRNOV (DATA DRIFT)
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
# MÉTRICAS DE MODEL DRIFT (REGRESSÃO / CLASSIFICAÇÃO)
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
# EXECUÇÃO PRINCIPAL
# ============================================================


def lambda_handler(event, context):
    record = event["Records"][0]
    bucket = record["s3"]["bucket"]["name"]
    key = urllib.parse.unquote_plus(
        record["s3"]["object"]["key"], encoding="utf-8"
    )

    print("=" * 60)
    print("MONITORAMENTO DE DRIFT MULTI-TENANT AWS")
    print("=" * 60)
    print("Arquivo capturado:", key)

    parts = key.split("/")

    # Exemplo: inference/modelo_01/2026-07-29.csv
    if len(parts) < 3 or parts[0] != "inference":
        print("Arquivo fora da estrutura 'inference/{endpoint_id}/{data}.csv'")
        return {"statusCode": 200, "body": "Ignorado"}

    endpoint_id = parts[1]
    filename = parts[-1]
    data_id = filename.replace(".csv", "")

    # Mapeamento dos endereços conforme a documentação
    baseline_key = f"baseline/{endpoint_id}.csv"
    ground_truth_key = f"ground_truth/{endpoint_id}/{filename}"
    data_drift_report_key = f"reports/{endpoint_id}/data_drift/{data_id}.json"
    model_drift_report_key = f"reports/{endpoint_id}/model_drift/{data_id}.json"

    print("Endpoint ID:", endpoint_id)
    print("Data/Lote:", data_id)

    # 1. Carregar Arquivo de Inferência
    try:
        inference_text = read_s3_text(bucket, key)
        inference_data = parse_csv_all_columns(inference_text)
    except Exception as e:
        print(f"Erro ao ler inferência: {str(e)}")
        return {"statusCode": 500, "body": "Erro ao ler inferencia"}

    # ============================================================
    # EXECUÇÃO DO DATA DRIFT
    # ============================================================

    if file_exists(bucket, baseline_key):
        baseline_text = read_s3_text(bucket, baseline_key)
        baseline_data = parse_csv_all_columns(baseline_text)

        ks_statistics = {}
        drift_detected = False

        for col_name, inf_values in inference_data.items():
            if col_name in baseline_data and len(inf_values) > 0:
                base_values = baseline_data[col_name]

                ks_stat = simple_ks_test(base_values, inf_values)
                ks_statistics[col_name] = round(ks_stat, 4)

                if ks_stat > KS_THRESHOLD:
                    drift_detected = True

        data_drift_payload = {
            "endpoint": endpoint_id,
            "drift_detected": drift_detected,
            "ks_statistics": ks_statistics,
        }

        save_s3_json(bucket, data_drift_report_key, data_drift_payload)
        print(f"Relatório de Data Drift salvo em: s3://{bucket}/{data_drift_report_key}")
    else:
        print(f"Baseline 's3://{bucket}/{baseline_key}' não encontrado. Data Drift ignorado.")

    # ============================================================
    # EXECUÇÃO DO MODEL DRIFT (SE GROUND TRUTH ESTIVER DISPONÍVEL)
    # ============================================================

    if file_exists(bucket, ground_truth_key):
        ground_truth_text = read_s3_text(bucket, ground_truth_key)
        ground_truth_data = parse_csv_all_columns(ground_truth_text)

        target_col = None
        for col in ground_truth_data.keys():
            if col in inference_data:
                target_col = col
                break

        if target_col:
            y_pred = inference_data[target_col]
            y_true = ground_truth_data[target_col]

            metrics = calculate_regression_metrics(y_true, y_pred)

            model_drift_payload = {
                "endpoint": endpoint_id,
                "metrics": metrics,
                "model_drift": False,
            }

            save_s3_json(bucket, model_drift_report_key, model_drift_payload)
            print(f"Relatório de Model Drift salvo em: s3://{bucket}/{model_drift_report_key}")
        else:
            print("Não foi encontrada coluna correspondente entre Inferencia e Ground Truth.")
    else:
        print(f"Ground Truth ainda não disponível em 's3://{bucket}/{ground_truth_key}'.")

    return {
        "statusCode": 200,
        "body": json.dumps({"status": "Sucesso", "endpoint": endpoint_id}),
    }
