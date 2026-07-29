
# Monitoramento de Drift de Multiplos Modelos na AWS

<p align="justify">Este projeto implementa uma solucao serverless, automatizada e de baixo custo para monitoramento de Data Drift em pipelines de Machine Learning multi-tenant na AWS. A arquitetura e totalmente orientada a eventos, acionada via Amazon S3 e executada atraves do AWS Lambda em Python 3.11, utilizando uma abordagem estrita via CLI e sem dependencia de interfaces visuais pesadas.</p>

---

## Arquitetura do Sistema

<p align="justify">A solucao utiliza uma estrutura de diretorios padronizada dentro do S3 para separar os dados de referencia (baseline) dos dados coletados em tempo real durante as predicoes (inference). Quando um novo lote de inferencia e carregado no S3, um evento dispara automaticamente a funcao Lambda para realizar o teste estatistico Kolmogorov-Smirnov (KS) e gerar o relatorio final em formato JSON.</p>

<p align="justify">O fluxo de dados segue a estrutura abaixo:</p>

- `s3://$BUCKET_NAME/baseline/{endpoint_id}.csv`: Contem a distribuicao de referencia historica utilizada no treinamento do modelo.
- `s3://$BUCKET_NAME/inference/{endpoint_id}/{data}.csv`: Lotes de inferencia do ambiente de producao. O upload nesta pasta dispara a validacao.
- `s3://$BUCKET_NAME/reports/{endpoint_id}/{data}.json`: Relatorio final persistido com o resultado da distancia KS e flag de deteccao de drift por variavel.

---

## Pre-requisitos e Variaveis de Ambiente

<p align="justify">Antes de iniciar a implantacao via AWS CLI, certifique-se de ter o utilitario configurado com as credenciais adequadas e defina as variaveis globais do terminal:</p>

```bash
export AWS_REGION="us-east-1"
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export BUCKET_NAME="bucket-drift-${ACCOUNT_ID}"
export LAMBDA_NAME="data-drift-detector"
export ROLE_NAME="DriftLambdaRole"
```

---

## Passo a Passo de Implantacao

### 1. Criar a IAM Role e Anexar Politicas de Acesso

<p align="justify">Criamos a Role que concede permissoes para a execucao da Lambda, gravacao de logs no CloudWatch e acesso de leitura e escrita no Amazon S3.</p>

```bash
cat <<EOF> trust-policy.json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
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

### 2. Criar o Bucket S3 Unico

<p align="justify">Criamos o bucket S3 globalmente exclusivo utilizando o ID da conta AWS como sufixo para evitar conflitos de namespace.</p>

```bash
aws s3api create-bucket \
    --bucket $BUCKET_NAME \
    --region $AWS_REGION
```

---

### 3. Empacotar o Codigo da Funcao Lambda

<p align="justify">Empacote o arquivo lambda_function.py previamente criado para envio a AWS.</p>

```bash
zip function.zip lambda_function.py
```

---

### 4. Deploy da Funcao Lambda e Permissoes de Invocacao

<p align="justify">Criamos a funcao no AWS Lambda e atribuimos a permissao necessaria para que o Amazon S3 possa invoca-la automaticamente quando novos arquivos forem enviados.</p>

```bash
aws lambda create-function \
    --function-name $LAMBDA_NAME \
    --runtime python3.11 \
    --role "arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}" \
    --handler lambda_function.lambda_handler \
    --zip-file fileb://function.zip \
    --timeout 30 \
    --memory-size 128 \
    --region $AWS_REGION

aws lambda add-permission \
    --function-name $LAMBDA_NAME \
    --statement-id s3-trigger-permission \
    --action lambda:InvokeFunction \
    --principal s3.amazonaws.com \
    --source-arn "arn:aws:s3:::${BUCKET_NAME}" \
    --region $AWS_REGION
```

---

### 5. Configurar o Gatilho do Evento S3

<p align="justify">Configuramos a notificacao do bucket para disparar automaticamente a funcao Lambda apenas quando arquivos CSV forem enviados para o prefixo <code>inference/</code>.</p>

```bash
cat <<EOF> s3-notification.json
{
  "LambdaFunctionConfigurations": [
    {
      "LambdaFunctionArn": "arn:aws:lambda:${AWS_REGION}:${ACCOUNT_ID}:function:${LAMBDA_NAME}",
      "Events": ["s3:ObjectCreated:*"],
      "Filter": {
        "Key": {
          "FilterRules": [
            {
              "Name": "prefix",
              "Value": "inference/"
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

## Validacao e Teste do Pipeline

<p align="justify">Para validar o funcionamento completo da arquitetura, enviamos arquivos contendo a distribuicao de referencia e um novo lote de inferencia. O upload do arquivo de inferencia dispara automaticamente a funcao Lambda, que executa o teste estatistico e gera o relatorio JSON.</p>

### 1. Upload dos Dados para o Amazon S3

```bash
aws s3 cp baseline_test.csv \
    s3://$BUCKET_NAME/baseline/estufa_01.csv

aws s3 cp inference_test.csv \
    s3://$BUCKET_NAME/inference/estufa_01/2026-07-28.csv
```

### 2. Acompanhar a Execucao da Lambda

<p align="justify">Os logs da execucao podem ser acompanhados em tempo real atraves do Amazon CloudWatch Logs.</p>

```bash
aws logs tail /aws/lambda/$LAMBDA_NAME --follow
```

### 3. Verificar o Relatorio Gerado

<p align="justify">Ao termino da execucao, o relatorio contendo as metricas do teste KS e o indicador de Data Drift sera armazenado automaticamente na pasta de relatorios do bucket.</p>

```bash
aws s3 cp \
    s3://$BUCKET_NAME/reports/estufa_01/2026-07-28.json - | cat
```

---

## Metrica e Performance

<p align="justify">Durante os testes realizados no ambiente AWS, a funcao apresentou baixa latencia e reduzido consumo de memoria, caracteristicas importantes para arquiteturas serverless orientadas a eventos.</p>

| Metrica | Valor |
|---------|-------|
| Tempo medio de execucao | ~276 ms |
| Memoria maxima utilizada | 95 MB de 128 MB |
| Custo estimado por execucao | menor que 0.0000001 USD |

---

## Conclusao

<p align="justify">A arquitetura implementada permite monitorar automaticamente Data Drift em diversos modelos de Machine Learning utilizando uma unica funcao AWS Lambda. O uso de eventos do Amazon S3 elimina a necessidade de processos de monitoramento continuo, reduzindo custos operacionais e simplificando a manutencao. A utilizacao do teste estatistico Kolmogorov-Smirnov fornece uma forma objetiva de identificar alteracoes na distribuicao dos dados de entrada, permitindo que novos ciclos de treinamento sejam iniciados apenas quando realmente necessarios.</p>
````

