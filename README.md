# Agregador de Dados GTFS do DF

Scrape de dados públicos da API do DFTrans para elaboração de estudo de acessibilidade e equidade espacial em Transportes, para a disciplina de Modelagem em Transportes do PPGT/UnB.

## Contexto e Dados Abertos no Distrito Federal

O acesso a dados padronizados de transporte público no formato **General Transit Feed Specification (GTFS)** é um pilar indispensável para o planejamento urbano contemporâneo, a avaliação de equidade espacial e a formulação de políticas públicas de mobilidade baseadas em evidências. Feeds GTFS viabilizam o cálculo de acessibilidade cumulativa e temporal em motores modernos de roteamento multimodal, como o `r5py` (backend Conveyal R5) e o OpenTripPlanner, além de fomentarem a transparência pública e o desenvolvimento de soluções voltadas à sociedade civil.

No entanto, no Distrito Federal, o Governo do Distrito Federal (GDF) e seu órgão gestor de transportes (**Semob-DF**, anteriormente DFTrans) atualmente **não disponibilizam publicamente um feed GTFS estático oficial, aberto e versionado**, tampouco camadas geoespaciais vetoriais (Shapefile, GeoPackage ou WFS) completas e atualizadas no Geoportal DF ou no portal de dados abertos do DF (`dados.df.gov.br`). Os dados operacionais de itinerários, paradas e tabelas horárias encontram-se fragmentados em sistemas internos e portais web pontuais (`dfnoponto.semob.df.gov.br` / `bus2.info` e a API REST legada do DFTrans).

Este repositório busca suprir essa lacuna técnica e de transparência, oferecendo um pipeline reprodutível de engenharia de dados que extrai, valida, georreferencia linearmente e sintetiza os dados operacionais do transporte coletivo do DF em um dataset GTFS estático padrão (`gtfs_df.zip`), diretamente compatível com ferramentas acadêmicas de modelagem de transportes.

> Assim como um processo de tratamento de água consolida partículas suspensas, este agregador atua como um "floculador" de dados: ele transforma feeds de transporte brutos, fragmentados e dispersos em uma base de dados limpa, estruturada e pronta para ser utilizada em sistemas de roteamento e análise de mobilidade urbana.

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
