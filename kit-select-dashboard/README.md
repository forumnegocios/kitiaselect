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
├── dashboard-server.py         ← servidor local (porta 5680)
├── dashboard.html              ← interface do painel
├── dados/
│   ├── perfil-do-negocio.json  ← perfil do seu negócio
│   └── outputs/                ← outputs gerados pelo Claude
└── README.md
```

## Como os outputs aparecem aqui

As skills do Kit Select IA salvam os resultados automaticamente na pasta `dados/outputs/`. O dashboard detecta os arquivos novos e exibe sem precisar reiniciar.

## Suporte

Fórum Negócios Select · @forumnegociosselect · forumselect.com.br
