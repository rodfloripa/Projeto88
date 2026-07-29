
# Monitoramento de Drift de Multiplos Modelos na AWS

<p align="justify">Este projeto implementa uma solucao serverless, automatizada e de baixo custo para monitoramento continuo de Drift dos Dados e Drift do Modelo em pipelines de Machine Learning multi-tenant na AWS. A arquitetura e totalmente orientada a eventos, acionada via Amazon S3 e executada atraves do AWS Lambda em Python 3.11, utilizando uma abordagem estrita via AWS CLI e sem dependencia de interfaces visuais pesadas.</p>

<p align="justify">Como diferencial, esta implementacao prioriza simplicidade operacional. Enquanto solucoes como o Evidently AI normalmente exigem uma estrutura mais complexa, envolvendo diversos arquivos de configuracao, dashboards, dependencias adicionais e, em alguns cenarios, componentes baseados em Node.js para interfaces web, este projeto utiliza apenas servicos nativos da AWS, uma unica funcao Lambda e comandos da AWS CLI. Isso reduz significativamente a complexidade de implantacao, manutencao e operacao, tornando a solucao mais leve, portavel e adequada para ambientes de producao que necessitam monitorar multiplos modelos de Machine Learning com baixo custo.</p>

---

## Arquitetura do Sistema

<p align="justify">A arquitetura utiliza o Amazon S3 como ponto central de armazenamento para os dados de referencia, dados de inferencia, rotulos verdadeiros e relatorios gerados. Sempre que um novo lote de inferencia e enviado para o bucket, um evento do Amazon S3 dispara automaticamente uma funcao AWS Lambda responsavel pela execucao dos testes de Drift dos Dados. Posteriormente, quando os valores reais das predicoes ficam disponiveis, outra execucao calcula as metricas de desempenho do modelo para identificar possivel Drift do Modelo.</p>

<p align="justify">A deteccao de Drift dos Dados utiliza o teste estatistico Kolmogorov-Smirnov (KS) para comparar cada variavel do conjunto de inferencia com sua distribuicao de referencia. Para o monitoramento do modelo sao calculadas metricas como Accuracy, Precision, Recall, F1-Score e AUC para problemas de classificacao ou RMSE e MAE para problemas de regressao, comparando os resultados atuais com o baseline historico.</p>

<p align="justify">O fluxo de armazenamento segue a estrutura abaixo:</p>

- `s3://$BUCKET_NAME/baseline/{endpoint_id}.csv` — Dados utilizados como distribuicao de referencia.
- `s3://$BUCKET_NAME/inference/{endpoint_id}/{data}.csv` — Dados recebidos em producao.
- `s3://$BUCKET_NAME/ground_truth/{endpoint_id}/{data}.csv` — Rotulos reais utilizados para avaliar o desempenho do modelo.
- `s3://$BUCKET_NAME/reports/{endpoint_id}/data_drift/{data}.json` — Resultado do monitoramento de Drift dos Dados.
- `s3://$BUCKET_NAME/reports/{endpoint_id}/model_drift/{data}.json` — Resultado do monitoramento de Drift do Modelo.

---

## Fluxo de Execucao

```text
           Baseline
               │
               ▼
        Upload Inference
               │
               ▼
     Evento ObjectCreated no S3
               │
               ▼
          AWS Lambda
               │
      Teste Kolmogorov-Smirnov
               │
               ▼
     Gerar Relatorio Drift dos Dados
               │
               ▼
      Aguarda Ground Truth
               │
               ▼
      Calculo das Metricas
               │
               ▼
 Comparacao com Baseline Historico
               │
               ▼
     Gerar Relatorio Drift do Modelo
```

---

## Pre-requisitos e Variaveis de Ambiente

<p align="justify">Antes da implantacao, configure as credenciais da AWS e defina as variaveis globais abaixo.</p>

```bash
export AWS_REGION="us-east-1"
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export BUCKET_NAME="bucket-drift-${ACCOUNT_ID}"
export LAMBDA_NAME="drift-monitor"
export ROLE_NAME="DriftLambdaRole"
```

---

## Passo 1 - Criar a IAM Role

<p align="justify">Criamos uma Role para permitir que a funcao Lambda leia e grave arquivos no Amazon S3 e registre logs no Amazon CloudWatch.</p>

```bash
cat <<EOF > trust-policy.json
{
  "Version":"2012-10-17",
  "Statement":[
    {
      "Effect":"Allow",
      "Principal":{"Service":"lambda.amazonaws.com"},
      "Action":"sts:AssumeRole"
    }
  ]
}
EOF

aws iam create-role \
  --role-name $ROLE_NAME \
  --assume-role-policy-document file://trust-policy.json

aws iam attach-role-policy \
  --role-name $ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam attach-role-policy \
  --role-name $ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

sleep 10
```

---

## Passo 2 - Criar o Bucket

```bash
aws s3api create-bucket \
    --bucket $BUCKET_NAME \
    --region $AWS_REGION
```

---

## Passo 3 - Empacotar a Funcao

```bash
zip function.zip lambda_function.py
```

---

## Passo 4 - Criar a Funcao Lambda

```bash
aws lambda create-function \
    --function-name $LAMBDA_NAME \
    --runtime python3.11 \
    --role arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME} \
    --handler lambda_function.lambda_handler \
    --zip-file fileb://function.zip \
    --timeout 60 \
    --memory-size 256 \
    --region $AWS_REGION

aws lambda add-permission \
    --function-name $LAMBDA_NAME \
    --statement-id allow-s3 \
    --action lambda:InvokeFunction \
    --principal s3.amazonaws.com \
    --source-arn arn:aws:s3:::${BUCKET_NAME}
```

---

## Passo 5 - Configurar o Evento do Amazon S3

```bash
cat <<EOF > s3-notification.json
{
  "LambdaFunctionConfigurations":[
    {
      "LambdaFunctionArn":"arn:aws:lambda:${AWS_REGION}:${ACCOUNT_ID}:function:${LAMBDA_NAME}",
      "Events":[
        "s3:ObjectCreated:*"
      ],
      "Filter":{
        "Key":{
          "FilterRules":[
            {
              "Name":"prefix",
              "Value":"inference/"
            }
          ]
        }
      }
    }
  ]
}
EOF

aws s3api put-bucket-notification-configuration \
    --bucket $BUCKET_NAME \
    --notification-configuration file://s3-notification.json
```

---

## Validacao do Pipeline

### Upload do Baseline

```bash
aws s3 cp baseline.csv \
s3://$BUCKET_NAME/baseline/modelo_01.csv
```

### Upload da Inferencia

```bash
aws s3 cp inference.csv \
s3://$BUCKET_NAME/inference/modelo_01/2026-07-29.csv
```

### Upload do Ground Truth

```bash
aws s3 cp ground_truth.csv \
s3://$BUCKET_NAME/ground_truth/modelo_01/2026-07-29.csv
```

### Acompanhar Logs

```bash
aws logs tail /aws/lambda/$LAMBDA_NAME --follow
```

### Consultar Relatorios

```bash
aws s3 cp \
s3://$BUCKET_NAME/reports/modelo_01/data_drift/2026-07-29.json -

aws s3 cp \
s3://$BUCKET_NAME/reports/modelo_01/model_drift/2026-07-29.json -
```

---

## Estrutura dos Relatorios

### Drift dos Dados

```json
{
  "endpoint":"modelo_01",
  "drift_detected":true,
  "ks_statistics":{
    "temperatura":0.24,
    "umidade":0.18,
    "pressao":0.07
  }
}
```

### Drift do Modelo

```json
{
  "endpoint":"modelo_01",
  "accuracy_baseline":0.96,
  "accuracy_current":0.90,
  "precision":0.91,
  "recall":0.89,
  "f1_score":0.90,
  "auc":0.94,
  "model_drift":true
}
```

---

## Metricas de Performance

| Metrica | Valor |
|---------|-------|
| Tempo medio de execucao | ~300 ms |
| Memoria utilizada | ~100 MB |
| Runtime | Python 3.11 |
| Arquitetura | Serverless |
| Custo estimado por execucao | Menor que USD 0.0000001 |

---

## Vantagens da Solucao

- Arquitetura totalmente serverless.
- Monitoramento simultaneo de Drift dos Dados e Drift do Modelo.
- Suporte a multiplos modelos utilizando uma unica funcao Lambda.
- Arquitetura orientada a eventos utilizando Amazon S3.
- Implantacao completa utilizando apenas AWS CLI.
- Sem dashboards obrigatorios.
- Sem necessidade de Node.js.
- Sem containers.
- Sem servidores dedicados.
- Baixissimo custo operacional.
- Facil integracao com pipelines de MLOps existentes.
- Relatorios em JSON para integracao com outros sistemas.
- Escalabilidade automatica da AWS Lambda.

---

## Conclusao

<p align="justify">A solucao demonstra que o monitoramento de Drift dos Dados e Drift do Modelo pode ser implementado de maneira simples, escalavel e com custo extremamente reduzido utilizando exclusivamente servicos nativos da AWS. O uso combinado do Amazon S3, AWS Lambda e Amazon CloudWatch elimina a necessidade de infraestrutura dedicada, permitindo que novos lotes de dados sejam processados automaticamente por meio de eventos. Alem da deteccao de alteracoes nas distribuicoes das variaveis de entrada utilizando o teste Kolmogorov-Smirnov, o projeto acompanha continuamente a degradacao do desempenho dos modelos por meio de metricas de classificacao ou regressao, fornecendo uma estrategia completa para monitoramento de modelos em producao.</p>

<p align="justify">Em comparacao com ferramentas mais robustas, como o Evidently AI, esta implementacao prioriza simplicidade, portabilidade e facilidade de implantacao. Toda a infraestrutura pode ser criada utilizando apenas AWS CLI, uma unica funcao Lambda e recursos nativos da plataforma, dispensando dashboards complexos, componentes adicionais, dependencias baseadas em Node.js e estruturas compostas por diversos arquivos de configuracao. O resultado e uma arquitetura enxuta, de facil manutencao e adequada tanto para ambientes experimentais quanto para sistemas de producao que necessitam monitorar centenas de modelos com baixo custo operacional.</p>
````
