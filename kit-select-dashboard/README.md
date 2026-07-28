# Kit Select IA — Dashboard

Painel visual para acompanhar o uso das ferramentas do Kit Select IA.

## Como usar

**Windows:** duplo clique em `iniciar-dashboard.bat`  
**Mac:** duplo clique em `iniciar-dashboard.command`

Na primeira vez, o instalador baixa as dependências automaticamente (requer internet). Da segunda vez em diante, abre direto.

## Requisitos

- Python 3.8 ou superior
- Chrome, Edge ou Firefox

## Estrutura

```
kit-select-dashboard/
├── iniciar-dashboard.bat       ← Windows
├── iniciar-dashboard.command   ← Mac
├── dashboard-server.py         ← servidor local (porta 5432)
├── dashboard.html              ← interface do painel
├── dados/
│   ├── perfil-do-negocio.json  ← perfil do seu negócio
│   └── outputs/                ← outputs gerados pelo Claude
└── README.md
```

## Como os outputs aparecem aqui

As skills do Kit Select IA salvam os resultados automaticamente na pasta `dados/outputs/`. O dashboard detecta os arquivos novos e exibe sem precisar reiniciar.

## Aba "Meu progresso"

Mostra ao empresário o que ele já construiu com o kit. Tudo é calculado a partir dos outputs salvos em `dados/outputs/` — nenhum dado extra precisa ser preenchido, e nada sai da máquina.

O que aparece:

- **Tempo economizado** — soma do tempo médio que cada entregável levaria para ser feito à mão (tabela `MINUTOS_POR_ENTREGAVEL` em `dashboard-server.py`, com números propositalmente conservadores)
- **Entregáveis criados**, média por semana, ferramentas experimentadas (x/10), dias ativos e semanas seguidas de uso
- **Ritmo das últimas 8 semanas** — barras com a produção semanal
- **Mix por área** — quanto de Conteúdo / Vender / Atender / Mercado / Documentos, para mostrar onde o negócio está desequilibrado
- **Ranking de ferramentas** — quais o empresário mais usa
- **Constância dos últimos 3 meses** — um quadradinho por dia
- **Próximos passos** — ferramentas ainda não usadas, com o prompt pronto para copiar
- **Conquistas** — marcos simples (primeiro entregável, 10 entregáveis, kit completo, 4 semanas seguidas…)

Os números vêm do endpoint `GET /api/uso`.

Para ajustar a estimativa de tempo economizado, edite `MINUTOS_POR_ENTREGAVEL` no servidor — é o único parâmetro subjetivo da aba.

## Galerias de Mercado e Documentos

As abas **Mercado** e **Documentos** mostram os resultados salvos em galeria de cards, com prévia do texto e data. Ao clicar em um card, o resultado abre formatado (títulos, listas e tabelas) com três ações:

- **Copiar texto** — o conteúdo puro, pra colar onde quiser
- **Copiar prompt para nova versão** — copia um prompt pronto pra pedir outra versão daquele mesmo resultado ao Claude
- **Baixar PDF** — gera um PDF com a identidade do Fórum Negócios Select

Os dois primeiros botões também aparecem direto no card, como atalho.

### Download em PDF

O PDF é gerado pelo servidor com a biblioteca `reportlab`:

```bash
pip install reportlab
```

Sem ela o dashboard continua funcionando: o botão **Baixar PDF** abre a janela de impressão do navegador, onde é possível escolher "Salvar como PDF".

## Suporte

Fórum Negócios Select · @forumnegociosselect · forumselect.com.br
