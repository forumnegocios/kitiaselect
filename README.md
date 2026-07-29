# Kit Select IA

Kit de ferramentas de IA do **Fórum Negócios Select** para empresários. São 10 ferramentas que conduzem o usuário passo a passo, em linguagem simples, sem exigir conhecimento técnico.

Este repositório guarda o material de entrega dos mentorados: o plugin, o manual em PDF e o painel visual opcional.

> Material exclusivo dos mentorados do Fórum Negócios Select. Por favor, não redistribua estes arquivos.

## O que tem aqui

| Arquivo | O que é |
| --- | --- |
| `Kit-Select-IA-Manual-do-Mentorado.pdf` | Manual completo: instalação, uso no dia a dia e perguntas frequentes. **Comece por aqui.** |
| `kit-select-ia.plugin` | O kit em si, com as 10 ferramentas. É o arquivo essencial — instale no Claude Cowork. |
| `kit-select-dashboard/` | **Opcional.** Painel visual que guarda e organiza o que você gerou. O kit funciona perfeitamente sem ele. |
| `LEIA-PRIMEIRO.txt` | Orientação rápida entregue junto com os arquivos. |

## As 10 ferramentas

**Começar**

1. **Configurar meu negócio** — monta e salva o perfil da empresa (contexto + referências). Pode enriquecer com o site, o Instagram (prints ou texto) ou um documento (PDF, Word, PowerPoint, texto). Faça uma vez.

**Conteúdo**

2. **Mês de conteúdo** — calendário de 4 semanas, equilibrando educar, inspirar, vender e conectar.
3. **Legenda no meu tom** — legendas prontas, no tom da marca.
4. **Roteiro de Reels** — roteiro de vídeo curto a partir de um post do calendário.
5. **Descrição de design** — design system da marca (para o Claude Design) ou o visual de um post.

**Vender**

6. **Criar anúncio** — anúncios de venda em estruturas comprovadas (PAS e AIDA).
7. **Proposta comercial** — de itens soltos a uma proposta que vende.

**Atender**

8. **Banco de respostas de cliente** — respostas prontas para as perguntas mais comuns.

**Mercado**

9. **Pesquisa de mercado** — relatório de concorrentes (comunicação e produto) e decisões acionáveis.

**Documentos**

10. **Resumir documento** — resumo e pontos de atenção de contratos e arquivos.

Além dessas, o kit traz o **menu Select** (mostra as opções disponíveis) e o **instalador do painel**.

## Como instalar

### 1. O plugin

Pré-requisitos: **plano pago do Claude** e uso no **Claude Cowork** (aplicativo desktop). Acesso à web é recomendado — melhora o enriquecimento por site e a pesquisa de mercado; sem ele, as ferramentas funcionam com material colado ou anexado.

Baixe o `kit-select-ia.plugin` e instale no Claude Cowork. O passo a passo com telas está na **Parte 3** do manual — são cinco passos e leva menos de cinco minutos.

Depois de instalado, peça em linguagem natural: *"gerar o mês de conteúdo"*, *"criar anúncio"*, *"resumir documento"* — ou peça o **menu** para ver as opções.

Comece por **Configurar meu negócio**: ela salva um `perfil-do-negocio.md` na pasta de trabalho, e todas as outras ferramentas leem esse perfil para personalizar o resultado.

### 2. O painel (opcional)

Requer **Python 3.8+** e um navegador (Chrome, Edge ou Firefox).

- **Windows:** duplo clique em `kit-select-dashboard/iniciar-dashboard.bat`
- **Mac:** duplo clique em `kit-select-dashboard/iniciar-dashboard.command`

Na primeira vez, o instalador baixa as dependências automaticamente (requer internet). Depois disso, abre direto — o servidor local sobe na porta 5680.

As ferramentas do kit salvam os resultados em `kit-select-dashboard/dados/outputs/`. O painel detecta os arquivos novos e exibe sem precisar reiniciar. Pode ser instalado a qualquer momento, sem perder nada do que já foi gerado.

## Boas práticas

- Revise o conteúdo gerado antes de publicar ou enviar (dados, ofertas, promessas, valores).
- Em anúncios de áreas sensíveis (saúde, estética, jurídico), evite promessas de resultado.
- **Resumir documento** é apoio de leitura, não aconselhamento jurídico: confirme pontos importantes com um profissional e anonimize dados de terceiros.
- Na pesquisa de mercado, o relatório marca o que é inferência — confirme antes de decidir.
- As ferramentas geram texto e planejamento. A **imagem** é criada no Claude Design, no Canva ou por um designer.

## Estrutura do painel

```
kit-select-dashboard/
├── iniciar-dashboard.bat       ← Windows
├── iniciar-dashboard.command   ← Mac
├── dashboard-server.py         ← servidor local (porta 5680)
├── dashboard.html              ← interface do painel
├── img/                        ← ícones das ferramentas
└── dados/
    └── outputs/                ← resultados gerados pelo Claude
```

## Suporte

Travou em algum ponto do manual? Fale com a equipe do Fórum Negócios Select — é assim que melhoramos o material para os próximos Selects.

---

**Fórum Negócios Select** · [@forumnegociosselect](https://instagram.com/forumnegociosselect) · [forumselect.com.br](https://www.forumselect.com.br)
