

# Otimização de Bombeamento com Custo Mínimo

<p align="justify">

Este projeto apresenta a modelagem e a otimização de um sistema de bombeamento responsável por transportar água de um reservatório inferior para um reservatório superior. O objetivo é determinar a vazão de operação que atende à demanda diária de água com o menor custo possível de energia elétrica.

</p>

---

# 1. Visão Geral

<p align="justify">

Em sistemas de bombeamento, a escolha da vazão de operação representa um problema de otimização. Vazões maiores permitem transportar uma quantidade maior de água em um determinado período, porém também aumentam significativamente as perdas de carga na tubulação e a potência necessária para operar a bomba.

</p>

<p align="justify">

A relação entre a vazão, a altura manométrica, a potência e o consumo de energia produz um problema de decisão no qual é necessário encontrar um equilíbrio entre a capacidade de bombeamento e o custo operacional.

</p>

<p align="justify">

Neste projeto, a vazão $Q$ é tratada como variável de decisão. A otimização busca encontrar a vazão que minimiza o custo diário de energia, respeitando simultaneamente a demanda de água e os limites físicos do sistema.

</p>

---

# 2. Representação do Sistema

<p align="justify">

O sistema é composto por um reservatório inferior, uma tubulação de transporte e um reservatório superior localizado a uma determinada altura geométrica. A bomba fornece a energia necessária para vencer tanto a diferença de altura entre os reservatórios quanto as perdas de carga provocadas pelo escoamento da água na tubulação.

</p>

<p align="justify">

A representação esquemática do sistema é apresentada abaixo.

</p>

<br>

<p align="center">

<!-- INSERIR A FIGURA ESQUEMÁTICA DOS RESERVATÓRIOS AQUI -->

</p>

<br>

<p align="justify">

A figura deve representar o reservatório inferior, a bomba, a tubulação, o reservatório superior, a altura geométrica $H_g$ e a vazão $Q$ do sistema.

</p>

---

# 3. Dados do Sistema

<p align="justify">

O modelo considera as principais variáveis hidráulicas, geométricas e econômicas associadas ao sistema de bombeamento.

</p>

| Variável     | Descrição                                | Unidade      |
| ------------ | ---------------------------------------- | ------------ |
| $Q$          | Vazão bombeada                           | m³/s         |
| $H_g$        | Altura geométrica entre os reservatórios | m            |
| $h_f(Q)$     | Perda de carga na tubulação              | m            |
| $H$          | Altura total manométrica                 | m            |
| $\eta$       | Eficiência da bomba                      | adimensional |
| $\rho$       | Massa específica da água                 | kg/m³        |
| $g$          | Aceleração da gravidade                  | m/s²         |
| $L$          | Comprimento da tubulação                 | m            |
| $D$          | Diâmetro da tubulação                    | m            |
| $t$          | Tempo de operação diário                 | h            |
| $V_{diário}$ | Volume bombeado por dia                  | m³           |
| $Custo$      | Custo diário de energia                  | R$/dia       |

---

# 4. Perda de Carga

<p align="justify">

A perda de carga representa a energia dissipada pelo escoamento da água ao longo da tubulação. Essa perda depende de fatores como a vazão, o comprimento da tubulação, o diâmetro, a rugosidade e as características hidráulicas do sistema.

</p>

<p align="justify">

Para simplificar o problema de otimização, foi utilizado o modelo quadrático:

</p>

$$
h_f(Q) = KQ^2
$$

<p align="justify">

Nesse modelo, $K$ representa um coeficiente equivalente que reúne os efeitos das características hidráulicas da tubulação. Como a perda de carga cresce com o quadrado da vazão, aumentos na vazão provocam um crescimento cada vez maior da resistência ao escoamento.

</p>

---

# 5. Altura Total Manométrica

<p align="justify">

A altura total manométrica corresponde à energia por unidade de peso que a bomba precisa fornecer à água. Ela é composta pela altura geométrica entre os reservatórios e pela perda de carga da tubulação.

</p>

$$
H(Q) = H_g + h_f(Q)
$$

<p align="justify">

Substituindo o modelo de perda de carga, obtém-se:

</p>

$$
H(Q) = H_g + KQ^2
$$

<p align="justify">

Portanto, quando a vazão aumenta, a altura total necessária também aumenta devido ao crescimento da perda de carga.

</p>

---

# 6. Potência da Bomba

<p align="justify">

A potência necessária para o bombeamento é calculada considerando a massa específica da água, a aceleração da gravidade, a vazão, a altura total manométrica e a eficiência da bomba.

</p>

$$
P(Q)
====

\frac{\rho g Q H(Q)}{\eta}
$$

<p align="justify">

Substituindo a expressão da altura total, temos:

</p>

$$
P(Q)
====

\frac{\rho g Q\left(H_g + KQ^2\right)}{\eta}
$$

<p align="justify">

Essa equação mostra que a potência não cresce apenas de forma linear com a vazão. Como a perda de carga cresce com $Q^2$, a potência também sofre um aumento acelerado quando a vazão se torna elevada.

</p>

---

# 7. Custo Diário de Energia

<p align="justify">

O custo diário de operação é calculado a partir da potência consumida pela bomba, do tempo diário de funcionamento e da tarifa de energia elétrica.

</p>

<p align="justify">

Como a potência inicialmente é calculada em watts, ela é convertida para quilowatts antes do cálculo do custo.

</p>

$$
Custo(Q)
========

P_{kW}(Q)
\cdot
t
\cdot
Tarifa
$$

<p align="justify">

A função objetivo do problema é, portanto:

</p>

$$
\min_Q Custo(Q)
$$

<p align="justify">

O algoritmo de otimização procura a vazão que produz o menor custo diário de bombeamento dentro dos limites permitidos pelo sistema.

</p>

---

# 8. Restrição de Atendimento da Demanda

<p align="justify">

O sistema precisa bombear uma quantidade mínima de água por dia. O volume bombeado é calculado pela relação entre a vazão e o tempo de operação.

</p>

$$
V_{diário}
==========

Q
\cdot
t
\cdot
3600
$$

<p align="justify">

O fator $3600$ realiza a conversão do tempo de operação de horas para segundos, permitindo que a vazão em m³/s seja utilizada diretamente.

</p>

<p align="justify">

Para que a demanda seja atendida, é necessário que:

</p>

$$
Q
\cdot
t
\cdot
3600
\geq
Demanda
$$

<p align="justify">

A vazão mínima necessária para atender à demanda é determinada por:

</p>

$$
Q_{demanda}
===========

\frac{Demanda}
{t \cdot 3600}
$$

<p align="justify">

Essa vazão é comparada com os limites físicos do sistema para determinar a região viável da otimização.

</p>

---

# 9. Restrições do Problema

<p align="justify">

A otimização deve respeitar simultaneamente as restrições de atendimento da demanda e os limites físicos de operação da bomba e da tubulação.

</p>

<p align="justify">

A primeira restrição garante que o volume diário bombeado seja suficiente:

</p>

$$
Q
\cdot
t
\cdot
3600
\geq
Demanda
$$

<p align="justify">

A segunda restrição estabelece os limites operacionais da vazão:

</p>

$$
Q_{min}
\leq
Q
\leq
Q_{max}
$$

<p align="justify">

A altura total é determinada diretamente pela vazão:

</p>

$$
H
=

H_g
+
KQ^2
$$

---

# 10. Dados Utilizados no Exemplo

<p align="justify">

Para demonstrar a otimização, foi utilizado um sistema com altura geométrica de $30$ metros, tubulação com comprimento de $1000$ metros e diâmetro de $0,2$ metros. A demanda diária de água é de $500$ m³ e a tarifa de energia considerada é de R$ 0,80 por kWh.

</p>

| Parâmetro                | Valor        |
| ------------------------ | ------------ |
| Altura geométrica        | 30 m         |
| Comprimento da tubulação | 1000 m       |
| Diâmetro da tubulação    | 0,2 m        |
| Demanda diária           | 500 m³/dia   |
| Eficiência da bomba      | 75%          |
| Tempo de operação        | 24 h/dia     |
| Tarifa de energia        | R$ 0,80/kWh  |
| Modelo de perda de carga | $h_f = KQ^2$ |

---

# 11. Método de Otimização

<p align="justify">

A função custo é avaliada em função da vazão e o algoritmo de otimização procura o ponto que apresenta o menor custo diário dentro do intervalo permitido.

</p>

<p align="justify">

A solução final fornece a vazão ótima, a perda de carga correspondente, a altura total manométrica, a potência requerida, o volume bombeado por dia e o custo mínimo de energia.

</p>

<p align="justify">

O método também permite analisar diferentes vazões e visualizar como a alteração da vazão influencia o custo operacional, a potência da bomba, a altura manométrica e o volume diário bombeado.

</p>

---

# 12. Resultados da Otimização

<p align="justify">

Após a execução do algoritmo, são apresentados os principais resultados da solução ótima encontrada.

</p>

<p align="justify">

A vazão ótima corresponde ao ponto de operação que minimiza o custo diário de energia respeitando a demanda mínima de água e os limites físicos definidos para o sistema.

</p>

<p align="justify">

Os resultados analisados incluem a vazão ótima em m³/s e L/s, a perda de carga, a altura total manométrica, a potência da bomba, o volume bombeado por dia e o custo diário mínimo.

</p>

---

# 13. Análise do Trade-off entre Vazão e Custo

<p align="justify">

Aumentar a vazão permite transportar mais água por unidade de tempo. Entretanto, esse aumento também provoca um crescimento da perda de carga, que é proporcional ao quadrado da vazão no modelo utilizado.

</p>

<p align="justify">

Consequentemente, a bomba precisa fornecer uma altura manométrica maior e consumir mais potência. Em determinadas condições, o aumento da vazão pode fazer com que o crescimento do consumo de energia supere qualquer benefício operacional obtido com o bombeamento mais rápido.

</p>

<p align="justify">

O ponto ótimo representa o equilíbrio entre a necessidade de atender à demanda e o aumento do consumo energético causado pelo escoamento em vazões elevadas.

</p>

---

# 14. Visualização do Custo Diário

<p align="justify">

O primeiro gráfico apresenta o custo diário de energia em função da vazão. O ponto de menor custo identifica a vazão ótima encontrada pelo algoritmo.

</p>

<p align="center">

<!-- INSERIR A FIGURA DO GRÁFICO DE CUSTO DIÁRIO AQUI -->

</p>

---

# 15. Visualização da Potência da Bomba

<p align="justify">

O segundo gráfico apresenta a potência necessária para operar a bomba em diferentes vazões. O crescimento da potência está relacionado diretamente ao aumento da vazão e da altura total manométrica.

</p>

<p align="center">

<!-- INSERIR A FIGURA DO GRÁFICO DE POTÊNCIA AQUI -->

</p>

---

# 16. Visualização da Altura Manométrica e da Perda de Carga

<p align="justify">

O terceiro gráfico mostra a evolução da altura total manométrica e da perda de carga em função da vazão. A altura geométrica permanece constante, enquanto a perda de carga aumenta com o crescimento da vazão.

</p>

<p align="center">

<!-- INSERIR A FIGURA DO GRÁFICO DE ALTURA MANOMÉTRICA AQUI -->

</p>

---

# 17. Atendimento da Demanda Diária

<p align="justify">

O quarto gráfico compara o volume diário bombeado com a demanda mínima do sistema. Essa análise permite verificar visualmente se a vazão escolhida é suficiente para atender à necessidade diária de água.

</p>

<p align="center">

<!-- INSERIR A FIGURA DO GRÁFICO DE ATENDIMENTO DA DEMANDA AQUI -->

</p>

---

# 18. Conclusões dos Resultados

<p align="justify">

<!-- INSERIR AQUI AS CONCLUSÕES OBTIDAS A PARTIR DOS RESULTADOS E DOS GRÁFICOS -->

</p>

<p align="justify">

<!-- ANALISAR A VAZÃO ÓTIMA, O CUSTO MÍNIMO, A POTÊNCIA, A PERDA DE CARGA E O ATENDIMENTO DA DEMANDA -->

</p>

<p align="justify">

<!-- EXPLICAR O TRADE-OFF ENTRE AUMENTAR A VAZÃO E AUMENTAR O CONSUMO DE ENERGIA -->

</p>

---

# 19. Conclusão

<p align="justify">

O problema demonstra como técnicas de otimização podem ser aplicadas ao planejamento operacional de sistemas de bombeamento. A escolha da vazão não deve considerar apenas a capacidade de transportar água rapidamente, pois o aumento da vazão também provoca maiores perdas de carga e maior consumo de energia.

</p>

<p align="justify">

A modelagem utilizada relaciona a vazão, a perda de carga, a altura total manométrica, a potência da bomba e o custo diário de operação. Dessa forma, a solução ótima representa um equilíbrio entre o atendimento da demanda de água e a redução do custo energético.

</p>

<p align="justify">

A abordagem pode ser expandida para modelos hidráulicos mais detalhados, incluindo fatores de atrito, rugosidade da tubulação, perdas localizadas, curvas reais de desempenho da bomba, tarifas de energia variáveis ao longo do dia e múltiplos reservatórios.

</p>

<p align="justify">

<!-- INSERIR A CONCLUSÃO FINAL BASEADA NA FIGURA DOS RESERVATÓRIOS E NOS RESULTADOS OBTIDOS -->

</p>

Se quiser, também posso transformar esse README em um arquivo `.md` pronto para baixar, mantendo exatamente essa estrutura e o `<p align="justify">` em todas as linhas de texto.

