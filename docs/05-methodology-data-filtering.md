# Metodologia: Coleta, Limpeza e Filtragem de Dados de Transporte Público (DFTrans -> GTFS)

*Este documento foi estruturado para subsidiar diretamente a seção de Metodologia / Coleta de Dados do artigo/dissertação sobre acessibilidade e equidade espacial no Distrito Federal (PPGT/UnB).*

---

## 1. Contexto e Motivação da Engenharia Reversa

No Distrito Federal, a Secretaria de Transporte e Mobilidade (Semob-DF) não disponibiliza publicamente arquivos padronizados no formato *General Transit Feed Specification* (GTFS), tampouco camadas vetoriais abertas e atualizadas de itinerários e pontos de parada via GeoPortal ou WFS. 

Para viabilizar a modelagem computacional de acessibilidade multimodais com o motor de roteamento `r5py` (baseado na biblioteca Conveyal R5 / OpenTripPlanner), foi desenvolvido um pipeline automatizado de extração, estruturação e síntese GTFS a partir da API REST oficial de suporte operacional do DFTrans (`https://www.sistemas.dftrans.df.gov.br`).

---

## 2. Protocolo de Coleta e Auditoria

A extração seguiu um protocolo estrito de três etapas:

1. **Descoberta Cadastral e Avaliação de Limites de API**:
   * Avaliou-se empiricamente o comportamento da rota de busca textual `GET /linha/find/{termo}` na API do DFTrans. Verificou-se que o backend impõe um truncamento fixo (*hard cap*) de **30 registros por resposta** (consultas curinga como `%25` ou dígitos individuais (ex. `0` a `9`) retornam invariavelmente no máximo 30 itens). Em virtude dessa limitação sistêmica, o endpoint de busca textual é inadequado para a varredura automatizada completa da rede.
   * Para assegurar a integridade e oficialidade da coleta alinhada ao sistema oficial **DF no Ponto** (Semob-DF), o extrator automatizado (`extract.py`) opera a partir do inventário consolidado de linhas do sistema (`data/lines.json`), com suporte à adição direta de linhas recém-inauguradas via parâmetros de execução (`--lines`). A partir desse catálogo, o pipeline dispara requisições pontuais para a rota oficial `GET /linha/numero/{numero}` no servidor do DFTrans (`sistemas.dftrans.df.gov.br`), que opera por busca exata sem teto de paginação, retornando confiavelmente todos os sentidos operacionais, concessionárias e identificadores `sequencial` de cada itinerário.
2. **Extração Multidimensional por Linha**:
   * **Metadados Operacionais** (`/linha/numero/{numero}`): identificação de operadoras (concessionárias das 5 bacias operacionais), tipo de veículo e faixa tarifária;
   * **Traçado Geométrico** (`/percurso/linha/numero/{numero}/`): geometria do itinerário codificada originalmente em EPSG:3857 (Web Mercator);
   * **Paradas Regulamentadas** (`/parada/linha/{sequencial}/geo`): coordenadas georreferenciadas dos pontos de embarque e desembarque vinculados a cada sentido operacional;
   * **Tabelas Horárias** (`/horario/linha/numero/{numero}`): partidas programadas por faixa de dia (Dias Úteis, Sábado, Domingo/Feriado).
3. **Persistência Bruta e Rastreabilidade**:
   * Cada requisição foi armazenada de forma atômica e persistente em disco (`data/raw/{numero_linha}.json`), assegurando a auditabilidade acadêmica e a repetibilidade experimental sem sobrecarga aos servidores públicos.

---

## 3. Critérios de Limpeza, Filtragem e Exclusão

Para que um feed GTFS seja computacionalmente válido e não gere inconsistências topológicas ou erros de "viagem no tempo" (temporal backtracking) no motor R5, foram aplicados os seguintes filtros e regras de consistência:

| Critério de Validação | Condição de Exclusão / Ajuste | Justificativa Metodológica | Ação Registrada no Pipeline |
| :--- | :--- | :--- | :--- |
| **Integridade de Traçado** | Linhas sem geometria retornada ou com feições nulas/corrompidas. | O roteador `r5py` exige vetores contínuos para associar os padrões de viagem à malha viária do OpenStreetMap. | Exclusão de `trips.txt` e inclusão em `data/catalog/skipped_lines.json`. |
| **Extensão Mínima de Paradas** | Sentidos com menos de 2 paradas geolocalizadas. | Uma viagem válida requer, no mínimo, origem e destino com pontos de parada distintos. | Exclusão do sentido operacional correspondente; registro em log. |
| **Disponibilidade de Tabela Horária** | Linhas ativas no cadastro sem partidas cadastradas em `/horario`. | Linhas puramente administrativas, sazonais desativadas ou sem operação regular no período amostrado. | Descarte da geração de viagens estáticas (`trips.txt`); registro em log. |
| **Projeção e Ordenação Topológica** | Paradas com pequenas discrepâncias de vetor em relação ao eixo da via. | Evita inversão de sequência de atendimento por imprecisão de GPS/CAD. | Projeção ortogonal das paradas sobre a polilinha (`LineString`) e ordenação estritamente monotônica pela distância linear acumulada (`shape_dist_traveled`). |

---

## 4. Transformação de Coordenadas e Síntese Temporal

1. **Reprojeção Espacial**:
   As coordenadas de percurso foram reescaladas e transformadas de EPSG:3857 (metros) para o referencial elipsoidal WGS84 (EPSG:4326), adotando formulação analítica direta para máxima precisão decimal.
2. **Interpolação de Horários Intermediários e Diferenciação de Velocidades**:
   Como a API do DFTrans informa exclusivamente os horários de partida dos terminais de origem, os horários de chegada e partida em cada parada intermediária foram sintetizados a partir da distância acumulada ao longo do traçado (`shapes.txt`), associando tempo de embarque/desembarque fixo (*dwell time* de 30 segundos por parada) e velocidades comerciais operacionais estratificadas por tipologia de serviço:
   * **Linhas Convencionais (Alimentadoras e Troncais em Tráfego Misto)**: Velocidade média calibrada em **20 km/h**, representativa do tráfego urbano e paradas frequentes;
   * **Linhas BRT (Expresso DF Sul e Corredores Exclusivos)**: Velocidade média calibrada em **40 km/h** (alcançando picos de até 60 km/h em via segregada e paradas em estações BRT com pagamento antecipado), identificadas a partir dos metadados de frota (`tiposOnibus` contendo veículos Padron ou Articulado BRT) e códigos troncais operacionais (`TR 20`, `2201`, `2202`, `2205`, `2301`, etc.).
   
   Essa abordagem garante trajetórias monotônicas no espaço-tempo exigidas pelo algoritmo RAPTOR/R5, sem gerar anomalias de ultrapassagem ou retrocesso temporal.

