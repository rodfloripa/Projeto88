import json
import urllib.parse
import boto3

s3 = boto3.client('s3')

def simple_ks_test(data1, data2):
    n1, n2 = len(data1), len(data2)
    if n1 == 0 or n2 == 0:
        return 0.0
    
    d1_sort, d2_sort = sorted(data1), sorted(data2)
    all_vals = sorted(list(set(data1 + data2)))
    max_d = 0.0
    
    i1 = i2 = 0
    for v in all_vals:
        while i1 < n1 and d1_sort[i1] <= v:
            i1 += 1
        while i2 < n2 and d2_sort[i2] <= v:
            i2 += 1
        d = abs((i1 / n1) - (i2 / n2))
        if d > max_d:
            max_d = d
            
    return max_d

def parse_csv_column(csv_text, column_name):
    lines = csv_text.splitlines()
    if not lines:
        return []
    headers = lines[0].split(',')
    if column_name not in headers:
        return []
    idx = headers.index(column_name)
    
    values = []
    for line in lines[1:]:
        parts = line.split(',')
        if len(parts) > idx:
            try:
                values.append(float(parts[idx]))
            except ValueError:
                pass
    return values

def lambda_handler(event, context):
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    
    parts = key.split('/')
    if len(parts) < 3 or parts[0] != "inference":
        print(f"[SKIP] Arquivo fora da pasta de inferência: {key}")
        return {'statusCode': 200, 'body': 'Ignored'}
    
    endpoint_id = parts[1]
    filename = parts[-1].replace('.csv', '.json')
    print(f"[INFO] Processando drift para Endpoint: {endpoint_id}")
    
    curr_obj = s3.get_object(Bucket=bucket, Key=key)
    curr_text = curr_obj['Body'].read().decode('utf-8')
    
    baseline_key = f"baseline/{endpoint_id}.csv"
    try:
        ref_obj = s3.get_object(Bucket=bucket, Key=baseline_key)
        ref_text = ref_obj['Body'].read().decode('utf-8')
    except s3.exceptions.NoSuchKey:
        print(f"[ERRO] Baseline nao encontrado em s3://{bucket}/{baseline_key}")
        return {'statusCode': 400, 'body': 'Baseline not found'}

    features_to_check = ['temperature', 'humidity', 'co2_level']
    drift_summary = {
        "endpoint_id": endpoint_id,
        "processed_file": key,
        "features": {}
    }
    
    for feat in features_to_check:
        ref_vals = parse_csv_column(ref_text, feat)
        curr_vals = parse_csv_column(curr_text, feat)
        
        if ref_vals and curr_vals:
            ks_stat = simple_ks_test(ref_vals, curr_vals)
            has_drift = ks_stat > 0.20
            
            drift_summary["features"][feat] = {
                "ks_distance": round(ks_stat, 4),
                "has_drift": has_drift
            }

    # Salva o resultado em formato JSON na pasta reports/ do S3
    report_key = f"reports/{endpoint_id}/{filename}"
    s3.put_object(
        Bucket=bucket,
        Key=report_key,
        Body=json.dumps(drift_summary, indent=2),
        ContentType='application/json'
    )
    
    print(f"[SUCCESS] Relatório salvo em: s3://{bucket}/{report_key}")
    return {'statusCode': 200, 'body': json.dumps(drift_summary)}
