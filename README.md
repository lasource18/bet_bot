# Automated Sports Betting Bot

A sophisticated automated sports betting system that implements various betting strategies across multiple sportsbooks. Currently focused on soccer betting using a match rating odds system, but designed to be extensible for other sports and strategies.

## 🎯 Features

- **Modular Architecture**: Built with extensibility in mind using abstract base classes and factory patterns
- **Multiple Sportsbooks Support**: Currently implements Pinnacle, with framework for adding more
- **Advanced Betting Strategies**: Implements a sophisticated match rating system for soccer
- **Automated Execution**: Handles bet placement, balance checking, and session management
- **Risk Management**: Implements bankroll management and staking strategies
- **Comprehensive Reporting**: Generates detailed reports and logs for analysis
- **League-Specific Calibration**: Customized parameters for different soccer leagues

## 🏗️ Architecture

The project follows a clean, modular architecture:

```
src/
├── bot/                    # Sportsbook interaction implementations
│   ├── betting_bot.py      # Abstract base class for sportsbooks
│   └── betting_bot_factory.py
├── strategies/             # Betting strategy implementations
│   ├── strategy.py         # Abstract base class for strategies
│   ├── match_ratings.py    # Match rating odds system
│   └── strategy_factory.py
├── staking/               # Staking strategy implementations
└── helpers/               # Utility functions and helpers
```

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Virtual environment (recommended)
- Access to sportsbook accounts
- Historical match data

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/bet_bot.git
cd bet_bot
```

2. Create and activate virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure your environment:
- Copy `config.json.example` to `config.json`
- Update sportsbook credentials
- Configure league settings
- Set up database connection

### Running the Bot

```bash
python main.py --betting-strategy match_ratings --staking-strategy kelly --bookmaker pinnacle
```

## 📊 Match Rating System

The current implementation uses a sophisticated match rating system:

1. **Goal Superiority Rating**: Calculates team ratings based on goals scored/conceded in last 6 matches
2. **Match Rating**: Computes relative strength between teams
3. **Probability Distribution**: Converts ratings to win/draw/loss probabilities
4. **Fair Odds Calculation**: Derives fair odds from probabilities
5. **Value Betting**: Identifies bets where offered odds exceed fair odds

## 🔧 Extending the System

### Adding a New Sportsbook

1. Create a new class in `src/bot/` implementing `BettingBot`:
```python
from bot.betting_bot import BettingBot

class NewSportsbookBot(BettingBot):
    def login(self, credentials, logger, **kwargs):
        # Implement login logic
        pass
    
    def place_bet(self, odds, stake, outcome, game_info, logger, **kwargs):
        # Implement bet placement
        pass
    
    # Implement other required methods
```

2. Register the new bot in `BettingBotFactory`

### Adding a New Betting Strategy

1. Create a new class in `src/strategies/` implementing `Strategy`:
```python
from strategies.strategy import Strategy

class NewStrategy(Strategy):
    def compute(self, home, away, betting_strategy, logger):
        # Implement strategy logic
        pass
```

2. Register the new strategy in `StrategyFactory`

### Adding a New Staking Strategy

1. Create a new class in `src/staking/` implementing `StakingStrategy`:
```python
from staking.staking_strategy import StakingStrategy

class NewStakingStrategy(StakingStrategy):
    def compute_stake(self, bankroll, odds, probability, **kwargs):
        # Implement staking logic
        pass
```

2. Register the new staking strategy in `StakingFactory`

## 📈 Performance Monitoring

The system generates comprehensive reports:
- Daily betting logs
- Performance metrics
- Bankroll tracking
- Strategy analysis

View reports in the `reports/` directory.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔒 Security

- Never commit credentials or sensitive information
- Use environment variables for API keys
- Implement proper error handling and logging
- Follow sportsbook terms of service
