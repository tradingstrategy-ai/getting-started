 # Getting started
 
- This is an example repository for [Trading Strategy framework](https://tradingstrategy.ai) to 
  get started bringing your [algorithmic trading strategy](https://tradingstrategy.ai/glossary/algorithmic-trading) to decentralised finance
- This allows you to develop and backtest your trading strategies against DeFi and [Binance CEX](https://tradingstrategy.ai/glossary/cex) data

# Prerequisites

- Github user account 
  - The Docker container image running the development environment is hosted on [Github Container Registry](https://github.com/features/packages)
- Basic Python and data science knowledge
  - Python scripting
  - Pandas
  - Jupyter Notebook
- Basic algorithmic trading knowledge 
  - Understanding price chart and price action
  - Technical indicators

For complex strategies that process a lot of data we recommend running a local development environment with minimum of 16 GB RAM.

# What is contained

Click to open in your personal Github Codespaces:

- An example RSI breakout strategy for Bitcoin on Binance data
- An example EMA strategy for ETH on Uniswap v3 on Arbitrum

# How to run

- Open a notebook: 
- After opening the notebook click Run button Jupyter toolbar
  - Sometimes the toolbar does not appear, as Visual Studio Code fails to install extensions on the first run: in this case you need to restart your Visual Studio Code and it should work

![](./screenshots/jupyter-toolbar.png)

**Note to Mac users**: The current Docker image is built for Intel platform. If you run Dev Container
on your Mac computer with Visual Studio Code, the backtesting speed is slower than you would get otherwise. 

# How to add indicators

# How to visualise indicators

# H

# How do I develop a trading strategy
- 
- Have a trading idea
- Create the first prototype with data sources and indicators using centralised exchange data like Binance
  - Decentralised market have often too little history to make any kind of analysis
- Validate your backtest robustness by testing shifting timeframes around
- After happy with the strategy, Change the backtesting to real decentralised data
- Convert the backtest notebook to a Trading Strategy Python module
- Launch the live trading strategy

# Learning resources

- [Trading Strategy documentation](https://tradingstrategy.ai/docs/)
- [About Github Codespaces](https://github.com/features/codespaces)
- [About Visual Studio Dev Containers](https://code.visualstudio.com/docs/devcontainers/containers)

# Troubleshooting

- [Rebuilding Dev Containers for Github codespaces](https://docs.github.com/en/codespaces/developing-in-a-codespace/rebuilding-the-container-in-a-codespace)
- [Dev Container CLI](https://code.visualstudio.com/docs/devcontainers/devcontainer-cli)
- [Microsoft default Dev Container image for Python](https://github.com/devcontainers/images/tree/main/src/python)
- [Dev Container Github Action](https://github.com/devcontainers/ci/blob/main/docs/github-action.md)
- [Dev Container JSON reference](https://code.visualstudio.com/docs/devcontainers/create-dev-container)

Testing the Dev Container build:

```shell
devcontainer up --workspace-folder . 
```