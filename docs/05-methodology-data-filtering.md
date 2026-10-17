# Metodologia: Coleta, Limpeza e Filtragem de Dados de Transporte Público (DFTrans -> GTFS)

*Este documento foi estruturado para subsidiar diretamente a seção de Metodologia / Coleta de Dados do artigo/dissertação sobre acessibilidade e equidade espacial no Distrito Federal (PPGT/UnB).*

---

## 1. Contexto, Lacuna Científica e Motivação da Engenharia Reversa

No Distrito Federal, a Secretaria de Transporte e Mobilidade (Semob-DF) não disponibiliza publicamente arquivos padronizados no formato *General Transit Feed Specification* (GTFS), tampouco camadas vetoriais abertas e atualizadas de itinerários e pontos de parada via GeoPortal ou WFS.

Essa carência histórica de dados abertos teve consequências profundas na literatura científica nacional sobre transportes: até mesmo o principal estudo de referência sobre acessibilidade urbana no Brasil — o **Projeto Acesso a Oportunidades do Ipea** ([`github.com/ipea/acesso_oport/releases`](https://github.com/ipea/acesso_oport/releases) e pacote `aopdata`) — foi obrigado a classificar o Distrito Federal sob a modalidade restrita:

> `bsb | Brasilia | ativo + carro`

Enquanto metrópoles como São Paulo, Rio de Janeiro, Belo Horizonte, Curitiba e Porto Alegre foram modeladas com redes multimodais completas combinando caminhada e transporte público coletivo via GTFS, **Brasília teve seu transporte público inteiramente omitido no estudo do Ipea por ausência de dados padronizados**.

Em um território com intensa segregação socioespacial como o DF, onde as Regiões Administrativas periféricas de menor renda (Ceilândia, Samambaia, Sol Nascente, Planaltina, Santa Maria) concentram os trabalhadores dependentes do transporte coletivo e a oferta de empregos qualificados situa-se no Plano Piloto, restringir a análise aos modos ativos e ao automóvel oculta o abismo de desigualdade vivenciado pela população.

Para preencher essa lacuna pioneira e viabilizar a modelagem computacional de acessibilidade multimodal com o motor de roteamento `r5py` (baseado na biblioteca Conveyal R5 / OpenTripPlanner), foi desenvolvido este pipeline automatizado de extração, estruturação e síntese GTFS a partir da API REST oficial de suporte operacional do DFTrans (`https://www.sistemas.dftrans.df.gov.br`) e do portal Bus2/Mobilibus. A obtenção desse feed GTFS estático permite elevar a qualidade das análises de acessibilidade no DF, superando limitações prévias da literatura nacional.

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

### 3.1 Dinâmica Temporal da Rede: O Paradoxo "Mais Linhas ≠ Melhor Base"

Na modelagem de sistemas de transporte coletivo, a qualidade de uma base de dados não pode ser avaliada unicamente pela sua cardinalidade bruta (número total de linhas catalogadas). As redes de transporte público urbano são dinâmicas: linhas são frequentemente extintas, fundidas, divididas ou suspensas por decisões operacionais do poder concedente (Semob-DF).

Dessa forma, catálogos históricos ou obtidos por compilação ampla de múltiplas fontes podem reter "linhas fantasmas" — itinerários que constam nos cadastros administrativos do órgão, mas que já não operam na prática. A inclusão indiscriminada dessas linhas em modelos de acessibilidade (`r5py` / OpenTripPlanner) distorceria os resultados de pesquisa, superestimando artificialmente a conectividade e a equidade espacial de determinadas regiões administrativas.

Por essa razão, a metodologia adota um protocolo em dois níveis:

1. **Catálogo Amplo de Candidatas:** O arquivo mestre (`data/catalog/lines.json`, 933 linhas atualmente) captura a totalidade das linhas urbanas referenciadas nos sistemas DFTrans e Bus2.
2. **Filtro de Atividade Operacional Efetiva:** Durante a síntese GTFS, cada linha é submetida ao filtro de partidas ativas (`/horario/`). Se uma linha cadastrada não apresentar viagens reais programadas no horizonte temporal de análise, ela não é convertida em entidades `trips.txt`, sendo classificada e auditada em `data/catalog/skipped_lines.json`. Isso assegura que o feed final represente com precisão a oferta efetiva de mobilidade vivenciada pela população.

### 3.2 Reconstrução Topológica de Paradas: O Fallback de Buffer de 35 Metros e Linear Referencing

Como o endpoint oficial do DFTrans que associava paradas a cada itinerário (`GET /parada/linha/{sequencial}/geo`) encontra-se inoperante (retornando invariavelmente HTTP 404), foi necessário desenvolver um algoritmo espacial determinístico para reconstruir a sequência correta de atendimento de paradas ao longo de cada rota:

1. **Prioridade Operacional (DF no Ponto / Bus2):**
   O compilador tenta primeiramente extrair a sequência ordenada de paradas e coordenadas georreferenciadas a partir do cache operacional do Bus2 (`trip_details`). Quando essa lista possui pelo menos duas paradas válidas dentro do DF, ela é adotada diretamente.

2. **Fallback Espacial: O Corredor de Buffer de 35 Metros:**
   Quando a linha não dispõe de detalhamento no Bus2, o algoritmo executa uma amarração espacial contra o inventário mestre de paradas (`data/all_stops_df.geojson`, ~5.466 paradas em todo o DF):
   * **Criação da Faixa Envoltória:** Em vez de gerar raios de busca circulares ao redor de pontos isolados, o compilador gera um corredor poligonal contínuo de **35 metros** de largura em torno do eixo da via (`LineString.buffer(35.0)` em EPSG:3857).
   * **Calibração dos 35 Metros:** Essa distância métrica foi calibrada com base na morfologia viária de Brasília (largura padrão das pistas de rolamento, canteiros centrais divisores, baías de acostamento/desaceleração e calçadas onde se instalam os abrigos de ônibus do DFTrans). Um raio menor (ex.: 15m) perderia paradas em avenidas largas com canteiro central (como W3, L2 ou EPTG); um raio maior (ex.: 50m) capturaria indevidamente pontos de vias paralelas ou de quadras vizinhas.
   * **Indexação Espacial R-Tree (`shapely.STRtree`):** Para viabilizar computacionalmente a busca entre milhares de paradas e centenas de percursos sem incorrer em complexidade quadrática $O(N \times M)$, todas as 5.466 paradas mestres são carregadas em uma árvore espacial *Sort-Tile-Recursive* (`STRtree`). O índice identifica os pontos candidatos contidos no corredor em tempo sub-milissegundo.

3. **Projeção Ortogonal e Ordenação Monotônica (`LineString.project`):**
   Cada parada contida no corredor é projetada ortogonalmente sobre a geometria da rota em coordenadas planas (EPSG:3857), convertida para distância real em solo pelo fator de distorção de escala de Brasília ($\kappa \approx 0{,}9622$). As paradas são então ordenadas monotonicamente pela distância linear acumulada a partir do ponto de partida (`shape_dist_traveled`).

4. **Deduplicação por Limiar de 15 Metros:**
   Paradas consecutivas no traçado com distância linear inferior a **15 metros** são consolidadas, eliminando redundâncias causadas por duplicidades cadastrais ou por abrigos do sentido oposto da via que eventualmente caiam dentro da margem do buffer.

---

## 4. Transformação de Coordenadas e Síntese Temporal

1. **Reprojeção Espacial**:
   As coordenadas de percurso foram reescaladas e transformadas de EPSG:3857 (metros) para o referencial elipsoidal WGS84 (EPSG:4326), adotando formulação analítica direta para máxima precisão decimal.
2. **Interpolação de Horários Intermediários e Diferenciação de Velocidades**:
   * **Lacuna dos Dados Oficiais (DFTrans e Bus2):** A API do DFTrans informa exclusivamente os horários de partida dos terminais de origem (`/horario/linha/numero/{numero}`). Similarmente, o backend da aplicação Bus2 (`dfnoponto`) publica tabelas de partidas e offsets parciais para um subconjunto de viagens, mas não disponibiliza tempos de percurso reais ou programados parada a parada para a totalidade das mais de 930 linhas da rede.
   * **Requisito dos Motores de Roteamento Multimodal (`r5py` / R5 / RAPTOR):** O cálculo de acessibilidade temporal e equidade espacial depende de motores como o R5 (`r5py`) e o OpenTripPlanner, cujos algoritmos centrais (como o **RAPTOR** — *Round-Based Public Transit Routing* e o **CSA** — *Connection Scan Algorithm*) operam sobre grafos espaço-temporais. Sem horários definidos em cada parada intermediária em `stop_times.txt`:
     1. O algoritmo é incapaz de simular embarques e desembarques nas paradas intermediárias ao longo da viagem (limitando o atendimento unicamente ao terminal inicial);
     2. Não é possível calcular transbordos ou integrações temporais entre linhas distintas que se interceptam ao longo do trajeto (ex.: eixos W3, L2, EPTG, Rodoviária do Plano Piloto);
     3. Torna-se inviável determinar matrizes de tempo de viagem e indicadores de acessibilidade cumulativa (ex.: postos de trabalho ou equipamentos de saúde acessíveis em até 30, 45 ou 60 minutos).
   * **Formulação Cinemática Adotada:**
     Para solucionar essa ausência de forma determinística e reproduzível, os horários de passagem intermediários foram sintetizados por amarração espacial (*Linear Referencing* via `shapely`):
     * As paradas foram projetadas ortogonalmente sobre o eixo geométrico do traçado (`LineString` em EPSG:3857);
     * A distância linear projetada foi convertida para métrica real em solo aplicando o fator de distorção de escala de Brasília ($\kappa = \cos(-15{,}8^\circ) \approx 0{,}9622$);
     * O tempo de deslocamento em trânsito ($T_{\text{run}}$) foi calculado a partir de velocidades operacionais comerciais estratificadas por tipologia viária:
       * **Linhas Convencionais (Alimentadoras e Troncais em Tráfego Misto)**: Velocidade média calibrada em **20 km/h** (~5,56 m/s), representativa do tráfego urbano compartilhado e semáforos;
       * **Linhas BRT (Expresso DF Sul e Corredores Exclusivos)**: Velocidade média calibrada em **40 km/h** (~11,11 m/s), refletindo via segregada e embarque em nível;
     * Foi adicionado um tempo de permanência padrão (*dwell time*) de **30 segundos** ($\Delta t_{\text{dwell}}$) por parada atendida, correspondente ao tempo médio de embarque e desembarque de passageiros:
       $$t_{\text{arrival}}(i) = t_0 + \frac{d_i \cdot \kappa}{v_{\text{comercial}}} + i \cdot \Delta t_{\text{dwell}}$$
       $$t_{\text{departure}}(i) = t_{\text{arrival}}(i) + \Delta t_{\text{dwell}}$$

   Essa abordagem é amplamente respaldada na literatura de engenharia de transportes para construção de feeds GTFS a partir de cadastros com dados incompletos, garantindo trajetórias estritamente monotônicas no espaço-tempo e eliminando paradoxos de retrocesso temporal no grafo.

   * **Distinção Crítica entre Oferta Programada e Tempo Real sob Congestionamento:**
     É metodologicamente imperativo registrar que a interpolação cinemática modela a **oferta estática programada** do sistema (cenário de referência operacional planejado). Ela **não afere os tempos reais de percurso decorrentes de atrito e congestionamento dinâmico na malha viária**, que afetam severamente as viagens nos horários de pico (períodos de maior demanda pendular, nos quais a população das Regiões Administrativas periféricas se desloca ao Plano Piloto por eixos saturados como a Estrutural, EPTG, EPIA, EPNB e BR-020). Em condições reais de pico em tráfego misto, as velocidades médias operacionais frequentemente caem para patamares significativamente inferiores aos 20 km/h nominais, de modo que os tempos reais vivenciados pelos passageiros são substancialmente superiores aos computados nesta modelagem teórica. Essa distinção deve ser explicitada nas análises de acessibilidade como uma delimitação de feeds GTFS estáticos gerados na ausência de telemetria AVL/GPS em tempo real.

---

## 5. Leituras Complementares e Referências Bibliográficas

Para um levantamento completo da literatura, histórico de aplicação dessa metodologia pelo Instituto de Pesquisa Econômica Aplicada (**Ipea - Projeto Acesso a Oportunidades**) em cidades brasileiras sem GTFS oficial e citações em formato BibTeX prontas para uso, consulte o documento [`docs/further-reading.md`](further-reading.md).
