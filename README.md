# Agregador de Dados GTFS do DF

Scrape de dados públicos da API do DFTrans para elaboração de estudo de acessibilidade e equidade espacial em Transportes, para a disciplina de Modelagem em Transportes do PPGT/UnB.

## Contexto e Dados Abertos no Distrito Federal

O acesso a dados padronizados de transporte público no formato **General Transit Feed Specification (GTFS)** é um pilar indispensável para o planejamento urbano contemporâneo, a avaliação de equidade espacial e a formulação de políticas públicas de mobilidade baseadas em evidências. Feeds GTFS viabilizam o cálculo de acessibilidade cumulativa e temporal em motores modernos de roteamento multimodal, como o `r5py` (backend Conveyal R5) e o OpenTripPlanner, além de fomentarem a transparência pública e o desenvolvimento de soluções voltadas à sociedade civil.

No entanto, no Distrito Federal, o Governo do Distrito Federal (GDF) e seu órgão gestor de transportes (**Semob-DF**, anteriormente DFTrans) atualmente **não disponibilizam publicamente um feed GTFS estático oficial, aberto e versionado**, tampouco camadas geoespaciais vetoriais (Shapefile, GeoPackage ou WFS) completas e atualizadas no Geoportal DF ou no portal de dados abertos do DF (`dados.df.gov.br`). Os dados operacionais de itinerários, paradas e tabelas horárias encontram-se fragmentados em sistemas internos e portais web pontuais (`dfnoponto.semob.df.gov.br` / `bus2.info` e a API REST legada do DFTrans).

Essa lacuna histórica é tão profunda que até mesmo o principal estudo nacional de acessibilidade urbana — o **Projeto Acesso a Oportunidades do Ipea** ([`acesso_oport`](https://github.com/ipea/acesso_oport)) — foi obrigado a restringir a modelagem do DF exclusivamente aos modos ativos e carro particular (`bsb | Brasilia | ativo + carro`), deixando o transporte público da capital como uma lacuna aberta na literatura científica.

Este repositório busca suprir essa lacuna técnica e de transparência, oferecendo um *pipeline* reprodutível de engenharia de dados que extrai, valida, georreferencia linearmente e sintetiza os dados operacionais do transporte coletivo do DF em um dataset GTFS estático padrão (`gtfs_df.zip`), diretamente compatível com ferramentas acadêmicas de modelagem de transportes e viabilizando, pela primeira vez no ecossistema R5/`r5py`, a análise completa de equidade e acessibilidade por transporte público em Brasília.

> Assim como um processo de tratamento de água consolida partículas suspensas, este agregador atua como um "floculador" de dados: ele transforma feeds de transporte brutos, fragmentados e dispersos em uma base de dados limpa, estruturada e pronta para ser utilizada em sistemas de roteamento e análise de mobilidade urbana.

## Funcionalidades

* **Descoberta Oficial de Linhas Ativas:** Mapeamento sistemático de todas as linhas de ônibus urbanas ativas do Distrito Federal diretamente via backends operacionais oficiais (DFTrans e Bus2/Mobilibus), eliminando scraping frágil de fontes não-oficiais, e filtrando automaticamente linhas interestaduais da ANTT (Entorno do DF).
* **Integração de Múltiplos Backends (DFTrans + DF no Ponto):** Fusão dos traçados vetoriais do DFTrans com o cadastro operacional moderno do **DF no Ponto** (`dfnoponto.semob.df.gov.br` / `bus2.info`), aproveitando suas listas ordenadas de paradas, coordenadas físicas e grades de partidas atualizadas por calendário.
* **Extração Multithread Resiliente:** Coleta automatizada com `ThreadPoolExecutor`, controle de polidez com delays configuráveis e retentativas exponenciais com *jitter* frente a instabilidades de rede e códigos HTTP 429/5xx.
* **Georreferenciamento e Reprojeção Cartográfica:** Conversão rigorosa de coordenadas de Web Mercator (`EPSG:3857`) para WGS84 (`EPSG:4326`), com correção de distorção de escala local para Brasília $(\cos(-15{,}8^\circ) \approx 0{,}9622)$.
* **Ordenação Monotônica de Paradas via Shapely:** Utilização de *linear referencing* (`shapely.geometry.LineString.project`) para projetar e ordenar estritamente paradas ao longo do eixo geométrico de cada percurso, prevenindo retrocessos espaciais em motores de roteamento como `r5py`.
* **Síntese Cinemática de Horários Intermediários:** Como os sistemas públicos não fornecem matrizes estáticas completas de tempo, parada a parada, para todas as 930+ linhas, o compilador preenche os horários em `stop_times.txt` diferenciando a velocidade comercial de linhas convencionais (20 km/h) e corredores exclusivos BRT (40 km/h), acrescida de tempo de permanência padrão (30 segundos de *dwell time* por parada).
* **Compatibilidade Estrita com Especificação GTFS:** Geração completa das tabelas `agency.txt`, `routes.txt`, `stops.txt`, `trips.txt`, `stop_times.txt`, `calendar.txt` e `shapes.txt`, empacotadas no arquivo padrão `gtfs_df.zip`.
* **Auditoria e Controle de Qualidade:** Registro transparente de linhas incompletas ou omitidas em `skipped_lines.json`.

## Pré-requisitos

* **Python:** Versão 3.10 ou superior.
* **Bibliotecas Python:**
  * `shapely >= 2.0.0` (operações geométricas e linear referencing)
  * `pyproj >= 3.6.0` (transformações cartográficas e de CRS)
  * `pandas >= 2.0.0` (manipulação de tabelas tabulares e CSVs)
  * `requests >= 2.30.0` (cliente HTTP e sessões resilientes)
  * `cryptography >= 42.0.0` (decriptação de payloads e segurança)
* **Java (Opcional, para roteamento):** Java JDK 11 ou 21 (necessário caso execute análises com `r5py` ou Conveyal R5).

## Instalação

1. Clone este repositório:

   ```bash
   git clone https://github.com/zaymuel/gtfs-df.git
   cd gtfs-df
   ```

2. Instale as dependências do projeto:

   ```bash
   pip install -r requirements.txt
   ```

*(Opcional)* Caso prefira utilizar um ambiente virtual isolado (`.venv` ou Conda), sinta-se livre para ativá-lo antes do comando acima.

## Como Usar

O fluxo de processamento é dividido em etapas modulares e reprodutíveis:

1. **Descoberta do Catálogo de Linhas Ativas:**
   Executa a enumeração oficial das linhas urbanas do DF e gera o mapeamento para os identificadores do sistema Bus2:

   ```bash
   python scripts/discover_catalog.py
   ```

   *Saída:* `data/catalog/lines.json` e `data/catalog/bus2_route_map.json`.

2. **Extração dos Dados Brutos das Linhas:**
   Realiza o download paralelo e cortês dos dados espaciais do DFTrans (percursos e inventário mestre de paradas) combinados simultaneamente aos dados operacionais do **DF no Ponto (Bus2)** (grades de partidas e paradas com coordenadas físicas):

   ```bash
   python scripts/extract.py
   ```

   *Saída:* Arquivos brutos por linha em `data/raw/{numero_linha}.json` e inventário mestre em `data/all_stops_df.geojson`.

3. **Compilação e Síntese do GTFS:**
   Processa os arquivos brutos combinando a malha geométrica com os dados do **DF no Ponto** (priorizando suas paradas físicas e tabelas horárias), aplicando projeção linear Shapely, modelagem tarifária e preenchimento cinemático de horários intermediários:

   ```bash
   python scripts/build_gtfs.py
   ```

   *Saída:* Arquivo compactado pronto para modelagem em `data/gtfs/gtfs_df.zip`.

   > **Dica:** A síntese adota prioritariamente as paradas e partidas do DF no Ponto. Para paradas intermediárias onde a API não fornece offsets estáticos, aplica-se o modelo cinemático padrão (20 km/h convencional, 40 km/h BRT e 30s de parada por ponto). Para customizar esses valores antes de executar, consulte a seção [Customização de Velocidades e Parâmetros Operacionais](#customização-de-velocidades-e-parâmetros-operacionais) logo abaixo.

4. **Auditoria de Integridade dos Portais:**
   Compara catálogos, detecta iframes e valida a integridade contra a página oficial da Semob-DF:

   ```bash
   python scripts/audit_dfnoponto.py
   ```

5. **Execução de Testes Automatizados:**
   Valida a monotonicidade temporal e espacial, conversão de CRS, modelagem tarifária, cifra Bus2, cliente HTTP resiliente e formatação GTFS com medição de cobertura:

   ```bash
   python tests/run_tests.py
   ```

   Ou diretamente via `pytest`:

   ```bash
   pytest tests/ -v --cov=scripts --cov-report=term-missing
   ```

### Customização de Velocidades e Parâmetros Operacionais

As premissas cinemáticas utilizadas para derivar os horários intermediários e a síntese das viagens em `scripts/build_gtfs.py` estão **centralizadas no arquivo `scripts/config.py`**:

```python
# scripts/config.py (linhas 72 a 74)
SPEED_CONVENTIONAL_KMH = float(os.getenv("SPEED_CONVENTIONAL_KMH", "20.0"))   # Linhas convencionais
SPEED_BRT_KMH = float(os.getenv("SPEED_BRT_KMH", "40.0"))                     # BRT em corredor exclusivo
DWELL_TIME_SEC = int(os.getenv("DWELL_TIME_SEC", "30"))                       # Tempo de parada por ponto
```

#### Como alterar as velocidades

* **Opção 1 (Direta no arquivo):** Abra [`scripts/config.py`](scripts/config.py) em qualquer editor e altere os valores numéricos das variáveis mencionadas.
* **Opção 2 (Via variáveis de ambiente sem alterar código):**
  * PowerShell (Windows):

    ```powershell
    $env:SPEED_CONVENTIONAL_KMH="25.0"; $env:SPEED_BRT_KMH="45.0"; python scripts/build_gtfs.py
    ```

  * Bash / Linux / macOS:

    ```bash
    SPEED_CONVENTIONAL_KMH=25.0 SPEED_BRT_KMH=45.0 python scripts/build_gtfs.py
    ```

### Síntese e Interpolação de Horários Intermediários (`stop_times.txt`)

A extração de dados no Distrito Federal apresenta um desafio metodológico: nem a API legada do DFTrans nem o sistema DF no Ponto (Bus2) disponibilizam matrizes estáticas completas de tempo de percurso para a totalidade das 930+ linhas da rede. No entanto, motores de roteamento multimodal (`r5py` / OpenTripPlanner) exigem timestamps válidos em todas as paradas para simular embarques, desembarques e transferências no espaço-tempo.

Para solucionar essa ausência de forma matematicamente consistente, o compilador adota uma **abordagem híbrida**:
* Prioriza a sequência oficial de paradas, coordenadas físicas e partidas operacionais extraídas do **DF no Ponto**;
* Reconstrói a sequência topológica de paradas via **fallback espacial com corredor de buffer de 35 metros** e indexação R-Tree (`shapely.STRtree`) para linhas sem cobertura no Bus2 ([Metodologia § 3.2](docs/05-methodology-data-filtering.md#32-reconstrução-topológica-de-paradas-o-fallback-de-buffer-de-35-metros-e-linear-referencing));
* Interpola os horários intermediários faltantes via **projeção linear ortogonal** (*Linear Referencing* com `shapely`), derivando monotonicamente os instantes de chegada e saída a partir das velocidades comerciais configuradas (20 km/h convencional e 40 km/h BRT) e *dwell time* (30s).

> 📖 **Detalhamento Técnico e Matemático Completo:**  
> Toda a formulação analítica, deduções cinemáticas, fator de correção cartográfica de Brasília, código de referência e critérios de monotonicidade estão documentados no [**ADR 0002: Síntese e Interpolação de Stop Times**](docs/adr/0002-stop-times-estimation.md).  
> Para o enquadramento metodológico no artigo acadêmico e paralelos com a literatura do Ipea, consulte a [Metodologia](docs/05-methodology-data-filtering.md) e as [Leituras Recomendadas](docs/further-reading.md).

## Estrutura dos Dados de Saída

Os dados finais são disponibilizados no diretório `data/gtfs/` e reunidos no arquivo `gtfs_df.zip`:

| Arquivo GTFS | Descrição Técnica no Projeto |
| :--- | :--- |
| `agency.txt` | Metadados do órgão gestor de transportes do Distrito Federal (Semob-DF / DFTrans). |
| `routes.txt` | Catálogo de rotas e linhas de ônibus com prefixo, descrição, cor da bacia e tipologia (convencional vs. BRT). |
| `stops.txt` | Todas as paradas físicas de ônibus ativas georreferenciadas em WGS84 (`EPSG:4326`). |
| `trips.txt` | Viagens direcionais programadas (`IDA`, `VOLTA`, `CIRCULAR`) associadas aos seus percursos. |
| `stop_times.txt` | Horários de chegada e partida em cada parada intermediária gerados por interpolação física ([ADR 0002](docs/adr/0002-stop-times-estimation.md)). |
| `calendar.txt` | Horizontes e padrões semanais de operação (Dias Úteis, Sábados, Domingos/Feriados). |
| `shapes.txt` | Geometrias contínuas dos itinerários em WGS84 com distância acumulada (`shape_dist_traveled`). |
| `fare_attributes.txt` | Faixas tarifárias praticadas no DF em BRL (Circular R$ 2.70, Média R$ 3.80, Longa R$ 5.50). |
| `fare_rules.txt` | Mapeamento relacional de cada rota (`route_id`) à sua respectiva faixa tarifária. |

Adicionalmente, os seguintes relatórios e catálogos são gerados em `data/catalog/`:

* `data/catalog/lines.json`: Catálogo compacto e deduplicado de todas as linhas urbanas ativas do DF.
* `data/catalog/bus2_route_map.json`: Mapeamento entre número da linha DFTrans e identificadores Base36 do Bus2.
* `data/catalog/bus2_routes.json`: Catálogo mestre de rotas extraídas da API pública do Bus2/Mobilibus.
* `data/catalog/bus2_agencies.json`: Cadastro das concessionárias e bacias operacionais.
* `data/catalog/skipped_lines.json`: Registro de percursos sem cobertura de paradas ou sem grade horária válida.
* `data/catalog/out_of_bounds_stops.json`: Log de paradas que excedem a bounding box regulamentar do DF.

## Estrutura do Projeto

O repositório é estruturado de forma modular para evitar poluição da raiz e garantir clareza operacional:

```text
gtfs-df/
├── .github/
│   └── workflows/
│       └── ci.yml            # Pipeline de integração contínua (Ubuntu/Windows, Python 3.10-3.12, cov >= 75%)
├── scripts/                  # Programas e utilitários operacionais de extração e processamento
│   ├── config.py             # Configurações centralizadas, caminhos, velocidades e parâmetros HTTP/GTFS
│   ├── extract.py            # Extrator multithread paralelo com política cortês e backoff (supersedeu harvest_dftrans.py)
│   ├── build_gtfs.py         # Motor de projeção linear (shapely), síntese cinemática e empacotamento GTFS
│   ├── discover_catalog.py   # Enumeração oficial e desduplicação do catálogo de linhas ativas
│   ├── audit_dfnoponto.py    # Auditoria de catálogos do portal DF no Ponto e portais oficiais
│   ├── bus2_client.py        # Biblioteca cliente para API pública Bus2/Mobilibus (AES OpenSSL, Base36)
│   └── http_client.py        # Cliente HTTP com pool de sessões, retry cortês e jitter
├── tests/                    # Suíte de testes automatizados e medição de cobertura (offline, pytest)
│   ├── run_tests.py          # Runner programático de testes e validação de cobertura
│   ├── test_compiler.py      # Testes do compilador GTFS, reprojeção e modelagem de paradas
│   ├── test_clients.py       # Testes unitários de resiliência HTTP e decifração Bus2 AES
│   ├── test_catalog.py       # Testes de validação de linhas, filtragem ANTT e catalogação
│   └── test_audit_and_extract.py # Testes de extração multithread e auditoria de portais
├── data/
│   ├── catalog/              # Catálogos consolidados (lines.json, bus2_route_map.json, relatórios)
│   ├── raw/                  # Payloads brutos baixados por linha ({numero}.json)
│   ├── bus2 drafts/          # Bundles Angular JavaScript e HTMLs brutos isolados para fins de engenharia reversa (não incluso)
│   ├── htmls/                # Snapshots offline de páginas oficiais e relatórios de apoio (não incluso)
│   └── gtfs/                 # Tabelas GTFS finais e arquivo compactado gtfs_df.zip
├── docs/                     # Especificações arquiteturais e documentação de engenharia reversa
└── Python drafts/            # Scripts de sondagem exploratória e dumps temporários de pesquisa (não incluso)
```

## Limitações Conhecidas

* **Indisponibilidade do Endpoint de Paradas por Linha:** No servidor oficial do DFTrans, o endpoint `GET /parada/linha/{sequencial}/geo` encontra-se inoperante (retornando HTTP 404). Por essa razão, a amarração das paradas é realizada via *spatial snapping* com o inventário mestre de paradas (atualmente ~5.466 paradas, sujeito a atualização) e dados do sistema operacional Bus2.
* **Horários Intermediários Sintéticos (Oferta Programada vs. Tempo Real):** As tabelas horárias publicadas pelo poder público contêm exclusivamente os horários de partida nos terminais. Os horários nas paradas ao longo da viagem são derivados cinematicamente com base em velocidades médias nominais e *dwell time*, representando a **oferta teórica programada** do sistema. Eles **não refletem atrasos decorrentes de congestionamento dinâmico nos horários de pico**, que frequentemente elevam os tempos de viagem reais dos passageiros em vias saturadas de tráfego misto.
* **Rede Metroviária:** O feed atual contempla exclusivamente o modal ônibus. A integração da malha do Metrô-DF (`route_type = 1`) está mapeada no backlog do projeto ([Ticket 08](.scratch/gtfs-extraction/issues/08-metro-df-data-integration.md)).

## Contribuição

Contribuições são muito bem-vindas! Se você encontrar discrepâncias em traçados, inconsistências em códigos de linhas ou desejar aprimorar o modelo cinemático:

1. Faça um Fork do repositório.
2. Crie uma branch para sua modificação: `git checkout -b feature/minha-melhoria`.
3. Escreva testes para as novas funcionalidades na pasta de testes.
4. Envie um Pull Request detalhando as alterações.

Todo código submetido é regido sob os termos da licença **GNU AGPLv3**.

## Citação

Se você utilizar este software em sua pesquisa ou projeto, por favor, cite-o da seguinte forma:

```bibtex
@software{martin2026gtfs,
  author       = {Martin, Samuel},
  title        = {{Agregador de Dados GTFS do DF}},
  month        = {10},
  year         = {2026},
  publisher    = {GitHub},
  version      = {v1.0.0},
  url          = {https://github.com/zaymuel/gtfs-df/}
}
```

## Licença

Este projeto é licenciado sob a **GNU AGPLv3** (Affero General Public License versão 3), que garante que todas as melhorias e derivações deste agregador continuem abertas e acessíveis à comunidade, mesmo quando o software for executado como um serviço na web.

**O que você PODE fazer:**

* **Uso Comercial:** Você pode usar este software para fins comerciais.
* **Modificar e Distribuir:** Você pode alterar o código e distribuir suas próprias versões.
* **Uso Privado:** Você pode usar o código privadamente (embora existam regras se você o oferecer como serviço).

**O que você NÃO PODE fazer (Restrições e Condições):**

* **Não pode "fechar" o código-fonte:** Se você modificar e distribuir o software, **ou se disponibilizar o software para os usuários interagirem através de uma rede (como uma API ou site backend)**, você é obrigado a divulgar o código-fonte completo das suas modificações sob a mesma licença AGPLv3.
* **Não pode mudar a licença:** Qualquer trabalho derivado deve ser licenciado sob a AGPLv3.
* **Não pode remover avisos:** Você não pode remover os avisos de direitos autorais ou de licença originais do código.

Em resumo: você é livre para usar e lucrar com o código, mas se construir um serviço de rede com ele ou distribuí-lo, deve devolver suas contribuições e modificações à comunidade de código aberto.
