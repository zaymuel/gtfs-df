# Leituras Recomendadas (Further Reading)

*Compilação de referências bibliográficas, notas metodológicas do Ipea e literatura acadêmica sobre síntese de dados GTFS, interpolação cinemática e modelagem de acessibilidade urbana multimodal com o motor R5 / r5py.*

> [!WARNING]
> **Aviso de Conteúdo Gerado por Inteligência Artificial (IA):**
> Todo o conteúdo deste documento, incluindo sínteses conceituais, compilações metodológicas e referências bibliográficas, foi gerado com o auxílio de ferramentas de Inteligência Artificial. Enquanto não for integralmente auditado e revisado por um pesquisador humano, deve ser consultado com cautela e rigor crítico. Recomenda-se conferir diretamente as fontes primárias, publicações oficiais do Ipea e artigos originais antes de qualquer citação ou aproveitamento em dissertações, teses ou artigos científicos.

---

## 1. O Projeto Acesso a Oportunidades (Ipea) e a Síntese de GTFS

No Brasil, a ausência de feeds GTFS públicos, padronizados e versionados pelas autoridades locais de transporte é uma realidade na maioria esmagadora das cidades de médio e grande porte.

Para viabilizar o **Projeto Acesso a Oportunidades**, o Instituto de Pesquisa Econômica Aplicada (**Ipea**), sob a coordenação do pesquisador **Rafael H. M. Pereira**, desenvolveu uma das metodologias pioneiras no país para reconstruir e sintetizar feeds GTFS a partir de dados operacionais incompletos (cadastros municipais com itinerários em Shapefile/CAD e tabelas de partidas de terminais em planilhas/PDFs).

A abordagem adotada neste repositório para o Distrito Federal segue exatamente os preceitos científicos e matemáticos consolidados pelo Ipea e pela comunidade de transporte computacional:

1. **Amarração Espacial (*Linear Referencing*):** Projeção ortogonal dos pontos de parada sobre o eixo geométrico contínuo da rota (`LineString`), garantindo monotonicidade estrita de distância (`shape_dist_traveled`).
2. **Interpolação Cinemática de Horários:** Obtenção de horários intermediários em `stop_times.txt` pela divisão da distância projetada por uma velocidade comercial operacional média calibrada ($20\text{ km/h}$ em vias mistas convencionais e $40\text{ km/h}$ em corredores BRT), acrescida de tempo de permanência (*dwell time*) fixo por parada.
3. **Compatibilidade Roteador-Grafo:** Conformidade estrita com motores de roteamento baseados no algoritmo **RAPTOR** (Conveyal R5, `r5py`, `r5r` e OpenTripPlanner), prevenindo erros de retrocesso temporal (*backward travel*).

---

## 2. A Lacuna de Brasília no Banco de Dados do Ipea (`bsb: ativo + carro`)

Ao consultar a base de dados oficial e os lançamentos do projeto *Acesso a Oportunidades* ([`github.com/ipea/acesso_oport/releases`](https://github.com/ipea/acesso_oport/releases)), identifica-se uma constatação de grande valor acadêmico para o Distrito Federal:

```text
# Metadados de cobertura por município e modo de transporte (Ipea Acesso a Oportunidades)
bsb    Brasilia    ativo + carro
```

### 2.1 O que esse dado revela?

Enquanto outras grandes capitais brasileiras (como São Paulo, Rio de Janeiro, Belo Horizonte, Curitiba, Porto Alegre, Fortaleza e Recife) foram modeladas pelo Ipea combinando a malha viária com transporte público coletivo (**redes multimodais com GTFS**), **Brasília foi modelada unicamente para modos ativos (caminhada e bicicleta) e automóvel particular ("ativo + carro")**.

### 2.2 A Causa da Lacuna: Inexistência de GTFS Oficial Aberto

Essa restrição não decorreu de opção metodológica, mas sim da **indisponibilidade crônica de dados abertos no Distrito Federal**. Como o Governo do Distrito Federal (Semob-DF / DFTrans) nunca publicou um feed GTFS estático oficial e versionado, a equipe do Ipea não dispunha de um arquivo GTFS consolidado para alimentar o motor Conveyal R5 para a capital federal, sendo forçada a omitir o transporte público nas análises de acessibilidade de Brasília.

### 2.3 Oportunidade Científica e Contribuição deste Trabalho (PPGT/UnB)

Essa constatação confere um diferencial científico decisivo a este projeto:

1. **Ineditismo e Preenchimento de Lacuna Nacional:** Ao extrair, validar e sintetizar um feed GTFS completo (`gtfs_df.zip`) a partir da engenharia reversa das APIs operacionais do DFTrans e do Bus2, este repositório viabiliza, pela primeira vez no ecossistema R5 (`r5py`), a modelagem do transporte coletivo por ônibus em Brasília com base científica robusta.
2. **Modelagem da Rede Estrutural e Conexões de Transporte:** No Distrito Federal, as maiores distâncias e desigualdades socioespaciais ocorrem entre as Regiões Administrativas periféricas de menor renda (Ceilândia, Samambaia, Sol Nascente/Pôr do Sol, Planaltina, Santa Maria) e a área central do Plano Piloto. Avaliar a acessibilidade urbana assumindo que todos os indivíduos se deslocam por automóvel particular ou a pé distorce a realidade do DF, onde a imensa maioria dos trabalhadores depende estruturalmente da rede pública de ônibus. A incorporação do feed GTFS permite representar a topologia real das linhas, os transbordos em terminais e a oferta programada de viagens.
3. **Ressalva Metodológica Crucial — Oferta Teórica/Programada vs. Tempo Real de Viagem:** É indispensável pontuar que a interpolação cinemática adotada (distâncias físicas projetadas combinadas a velocidades médias nominais e tempos de parada fixos) modela o **nível de serviço programado/teórico** da rede. Ela **não reflete os tempos reais observados sob congestionamento dinâmico**, que afetam severamente as viagens nos horários de pico nos principais eixos viários do DF (Estrutural, EPTG, EPIA, EPNB, BR-020). Na prática operacional, os tempos reais gastos pelos passageiros da periferia tendem a ser substancialmente maiores do que os tempos programados pelo modelo cinemático, reforçando que os resultados representam um cenário de oferta nominal planejada.

---

## 3. Publicações Fundamentais do Ipea

### 3.1 Metodologia do Projeto Acesso a Oportunidades

* **Referência:** Pereira, R. H. M., Braga, C. K. V., Saraiva, M., Serra, B., Amaral, P. V. M., Gouveia, N., & Paez, A. (2019). *Desigualdades socioespaciais de acesso a oportunidades nas cidades brasileiras — 2019*. **Texto para Discussão nº 2535**, Instituto de Pesquisa Econômica Aplicada (Ipea).
* **URL:** [https://repositorio.ipea.gov.br/handle/11058/9586](https://repositorio.ipea.gov.br/handle/11058/9586)
* **Relevância para a Dissertação:** Detalha a metodologia nacional de coleta e estruturação de bases de transporte público de 20 grandes cidades brasileiras. Na Seção 3 ("Dados e Tratamento Metodológico"), os autores descrevem os desafios de ausência de GTFS oficial e o procedimento adotado para harmonizar trajetos, paradas e intervalos entre viagens. Registra explicitamente as cidades onde o modal transporte público não pôde ser incluído por falta de dados.

### 3.2 Modelagem Multimodal com o Motor R5

* **Referência:** Pereira, R. H. M., Saraiva, M., Herszenhut, D., Braga, C. K. V., & Conway, M. W. (2021). *r5r: Rapid Realistic Routing on Multimodal Transport Networks with R5 in R*. **Findings**, 21262.
* **DOI:** [10.32866/001c.21262](https://doi.org/10.32866/001c.21262)
* **Relevância para a Dissertação:** Artigo que formaliza o uso do backend Conveyal R5 (escrito em Java) no contexto acadêmico. Descreve em detalhes os requisitos exigidos pelo motor sobre as tabelas estáticas de GTFS (especialmente `stop_times.txt` e `shapes.txt`) e como os tempos de passagem são utilizados para computar matrizes de tempo de viagem porta-a-porta considerando caminhar, esperar, embarcar e transferir.

### 3.3 Conversão e Interpolação Espaço-Tempo (gtfs2gps)

* **Referência:** Pereira, R. H. M., Andrade, P. R., & Vieira, J. P. (2020). *gtfs2gps: Converting GTFS data to GPS-like records*. **Journal of Open Source Software (JOSS)**, 5(56), 2685.
* **DOI:** [10.21105/joss.02685](https://doi.org/10.21105/joss.02685)
* **Relevância para a Dissertação:** Apresenta a biblioteca desenvolvida pelo Ipea que realiza a interpolação temporal fina e a reconstrução de trajetórias a partir de feeds GTFS, validando matematicamente o uso de velocidades comerciais e cálculo de distâncias lineares acumuladas.

---

## 4. Repositórios de Código Aberto do Ipea

* **Projeto Acesso a Oportunidades (Scripts de Extração, Dados e GTFS):**  
  [https://github.com/ipea/acesso_oport](https://github.com/ipea/acesso_oport)  
  *Contém os pipelines completos e lançamentos de dados utilizados pelo Ipea para limpar e sintetizar dados de transporte público no Brasil.*

* **Pacote `r5r` (R) / `r5py` (Python):**  
  * `r5r`: [https://github.com/ipea/r5r](https://github.com/ipea/r5r)  
  * `r5py`: [https://github.com/r5py/r5py](https://github.com/r5py/r5py)  
  *Bibliotecas para roteamento multimodal rápido sobre redes viárias do OpenStreetMap (`.osm.pbf`) e feeds GTFS (`.zip`).*

* **Pacote `gtfs2gps`:**  
  [https://github.com/ipea/gtfs2gps](https://github.com/ipea/gtfs2gps)  
  *Utilitário para manipulação, validação e interpolação de trajetórias temporais de transporte coletivo.*

---

## 5. Literatura Internacional sobre Motores de Roteamento (RAPTOR / R5)

* **Algoritmo RAPTOR:**  
  Delling, D., Pajor, T., & Werneck, R. F. (2014). *Round-Based Public Transit Routing*. **Transportation Science**, 49(3), 591–604.  
  *Fundamentação teórica do algoritmo que tornou obsoleto o algoritmo de Dijkstra tradicional para redes de transporte público programadas por horários (timetables).*

* **Conveyal R5 e Acessibilidade Multimodal:**  
  Conway, M. W., Byrd, A., & van Eggermond, M. (2017). *Accounting for uncertainty and variation in accessible destinations for a complete transit network*. **Journal of Transport and Land Use**, 10(1), 1–25.  
  *Explica como a combinação de GTFS + OpenStreetMap permite estimar com precisão janelas de partida com perfis de tempo de viagem em vez de medições pontuais estáticas.*

---

## 6. Entradas BibTeX para Citação

```bibtex
@techreport{pereira2019acesso,
  title       = {Desigualdades socioespaciais de acesso a oportunidades nas cidades brasileiras: 2019},
  author      = {Pereira, Rafael H. M. and Braga, Carlos Kaue Vieira and Saraiva, Marcus and Serra, Bernardo and Amaral, Pedro V. M. and Gouveia, Nelson and Paez, Antonio},
  year        = {2019},
  institution = {Instituto de Pesquisa Econ{\^o}mica Aplicada (Ipea)},
  type        = {Texto para Discuss{\~a}o},
  number      = {2535},
  address     = {Bras{\'i}lia, DF},
  url         = {https://repositorio.ipea.gov.br/handle/11058/9586}
}

@article{pereira2021r5r,
  title     = {r5r: Rapid Realistic Routing on Multimodal Transport Networks with {R5} in {R}},
  author    = {Pereira, Rafael H. M. and Saraiva, Marcus and Herszenhut, Daniel and Braga, Carlos Kaue Vieira and Conway, Matthew Wigginton},
  journal   = {Findings},
  year      = {2021},
  pages     = {21262},
  publisher = {Network and Communication Studies},
  doi       = {10.32866/001c.21262}
}

@article{pereira2020gtfs2gps,
  title     = {gtfs2gps: Converting {GTFS} data to {GPS}-like records},
  author    = {Pereira, Rafael H. M. and Andrade, Pedro R. and Vieira, Jo{\~a}o Pedro},
  journal   = {Journal of Open Source Software},
  volume    = {5},
  number    = {56},
  pages     = {2685},
  year      = {2020},
  doi       = {10.21105/joss.02685}
}

@article{delling2014round,
  title     = {Round-Based Public Transit Routing},
  author    = {Delling, Daniel and Pajor, Thomas and Werneck, Renato F.},
  journal   = {Transportation Science},
  volume    = {49},
  number    = {3},
  pages     = {591--604},
  year      = {2014},
  publisher = {INFORMS},
  doi       = {10.1287/trsc.2014.0534}
}

@article{conway2017accounting,
  title     = {Accounting for uncertainty and variation in accessible destinations for a complete transit network},
  author    = {Conway, Matthew Wigginton and Byrd, Andrew and van Eggermond, Michael},
  journal   = {Journal of Transport and Land Use},
  volume    = {10},
  number    = {1},
  pages     = {1--25},
  year      = {2017},
  doi       = {10.5198/jtlu.2017.931}
}
```
