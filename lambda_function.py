
import json
import math
import urllib.parse
import boto3

s3 = boto3.client("s3")

# ============================================================
# CONFIGURAÇÕES
# ============================================================

FEATURES = ["temperature", "humidity", "co2_level"]

KS_THRESHOLD = 0.20

# Thresholds do Model Drift
RMSE_THRESHOLD = {"temperature": 0.50, "humidity": 2.00, "co2_level": 20.0}

MAE_THRESHOLD = {"temperature": 0.40, "humidity": 1.50, "co2_level": 15.0}


# ============================================================
# LEITURA CSV
# ============================================================


def parse_csv_column(csv_text, column_name):
    lines = csv_text.splitlines()

    if not lines:
        return []

    headers = lines[0].split(",")

    if column_name not in headers:
        return []

    idx = headers.index(column_name)
    values = []

    for line in lines[1:]:
        if not line.strip():
            continue

        cols = line.split(",")

        if len(cols) <= idx:
            continue

        try:
            values.append(float(cols[idx]))
        except ValueError:
            pass

    return values


# ============================================================
# TESTE KS
# ============================================================


def simple_ks_test(data1, data2):
    n1 = len(data1)
    n2 = len(data2)

    if n1 == 0 or n2 == 0:
        return 0.0

    d1 = sorted(data1)
    d2 = sorted(data2)

    values = sorted(list(set(data1 + data2)))

    i1 = 0
    i2 = 0
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
# MÉTRICAS DE REGRESSÃO
# ============================================================


def mae(y_true, y_pred):
    if len(y_true) == 0:
        return None

    return sum(abs(a - b) for a, b in zip(y_true, y_pred)) / len(y_true)


def mse(y_true, y_pred):
    if len(y_true) == 0:
        return None

    return sum((a - b) ** 2 for a, b in zip(y_true, y_pred)) / len(y_true)


def rmse(y_true, y_pred):
    value = mse(y_true, y_pred)

    if value is None:
        return None

    return math.sqrt(value)


# ============================================================
# LEITURA DOS ARQUIVOS S3
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


# ============================================================
# INÍCIO DA LAMBDA
# ============================================================


def lambda_handler(event, context):
    record = event["Records"][0]
    bucket = record["s3"]["bucket"]["name"]
    key = urllib.parse.unquote_plus(
        record["s3"]["object"]["key"], encoding="utf-8"
    )

    print("=" * 60)
    print("MONITORAMENTO DE DRIFT")
    print("=" * 60)
    print("Arquivo recebido:", key)

    parts = key.split("/")

    if len(parts) < 3 or parts[0] != "inference":
        return {"statusCode": 200, "body": "Ignorado"}

    endpoint = parts[1]
    filename = parts[-1]

    baseline_key = f"baseline/{endpoint}.csv"
    ground_truth_key = f"ground_truth/{endpoint}/{filename}"
    report_key = f"reports/{endpoint}/{filename.replace('.csv', '.json')}"

    print("Endpoint:", endpoint)
    print("Baseline:", baseline_key)
    print("Ground Truth:", ground_truth_key)

    # ============================================================
    # LEITURA DOS ARQUIVOS
    # ============================================================

    try:
        baseline_text = read_s3_text(bucket, baseline_key)
    except Exception as e:
        print("Baseline não encontrado.")
        print(str(e))
        return {"statusCode": 404, "body": "Baseline nao encontrado."}

    inference_text = read_s3_text(bucket, key)

    has_ground_truth = file_exists(bucket, ground_truth_key)

    if has_ground_truth:
        ground_truth_text = read_s3_text(bucket, ground_truth_key)
        print("Ground Truth encontrado.")
    else:
        ground_truth_text = None
        print("Ground Truth ainda não disponível.")

    # ============================================================
    # RELATÓRIO
    # ============================================================

    report = {
        "endpoint_id": endpoint,
        "processed_file": key,
        "data_drift": {},
        "model_drift": {},
    }

    # ============================================================
    # DATA DRIFT
    # ============================================================

    print("\n========== DATA DRIFT ==========")

    for feature in FEATURES:
        baseline = parse_csv_column(baseline_text, feature)
        inference = parse_csv_column(inference_text, feature)

        if len(baseline) == 0 or len(inference) == 0:
            continue

        ks = simple_ks_test(baseline, inference)
        drift = ks > KS_THRESHOLD

        print(
            feature,
            "KS=",
            round(ks, 4),
            "Drift=",
            drift,
        )

        report["data_drift"][feature] = {
            "ks_distance": round(ks, 4),
            "threshold": KS_THRESHOLD,
            "has_drift": drift,
        }

    # ============================================================
    # MODEL DRIFT
    # ============================================================

    if has_ground_truth:
        print("\n========== MODEL DRIFT ==========")

        for feature in FEATURES:
            prediction = parse_csv_column(inference_text, feature)
            truth = parse_csv_column(ground_truth_text, feature)

            if len(prediction) == 0 or len(truth) == 0:
                continue

            current_rmse = rmse(truth, prediction)
            current_mae = mae(truth, prediction)

            drift = (
                current_rmse > RMSE_THRESHOLD[feature]
                or current_mae > MAE_THRESHOLD[feature]
            )

            print(
                feature,
                "RMSE=",
                round(current_rmse, 4),
                "MAE=",
                round(current_mae, 4),
                "Drift=",
                drift,
            )

            report["model_drift"][feature] = {
                "rmse": round(current_rmse, 4),
                "mae": round(current_mae, 4),
                "rmse_threshold": RMSE_THRESHOLD[feature],
                "mae_threshold": MAE_THRESHOLD[feature],
                "has_drift": drift,
            }
    else:
        report["model_drift"] = {
            "status": "Ground Truth ainda nao disponivel."
        }

    # ============================================================
    # RESUMO GERAL
    # ============================================================

    total_data_drift = sum(
        1
        for v in report["data_drift"].values()
        if v.get("has_drift", False)
    )

    if (
        isinstance(report["model_drift"], dict)
        and "status" not in report["model_drift"]
    ):
        total_model_drift = sum(
            1
            for v in report["model_drift"].values()
            if v.get("has_drift", False)
        )
    else:
        total_model_drift = None

    report["summary"] = {
        "total_features": len(FEATURES),
        "features_with_data_drift": total_data_drift,
        "features_with_model_drift": total_model_drift,
        "ground_truth_available": has_ground_truth,
    }

    # ============================================================
    # SALVA RELATÓRIO NO S3
    # ============================================================

    s3.put_object(
        Bucket=bucket,
        Key=report_key,
        Body=json.dumps(report, indent=4),
        ContentType="application/json",
    )

    print("\n" + "=" * 60)
    print("RELATÓRIO GERADO")
    print("=" * 60)
    print(json.dumps(report, indent=4))
    print("=" * 60)
    print("Relatório salvo em:")
    print(f"s3://{bucket}/{report_key}")
    print("=" * 60)

    # ============================================================
    # RETORNO DA LAMBDA
    # ============================================================

    return {"statusCode": 200, "body": json.dumps(report, indent=4)}


