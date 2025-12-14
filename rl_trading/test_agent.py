import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv

from indicators import load_and_preprocess_data
from trading_env import ForexTradingEnv

def main():
    # 1. Load new test data
    #    If you want to test on the EXACT training data, use the same CSV as training
    #test_df = load_and_preprocess_data("data/EURUSD_Candlestick_1_Hour_BID_01.07.2020-15.07.2023.csv")
    test_df = load_and_preprocess_data("data/test_EURUSD_Candlestick_1_Hour_BID_20.02.2023-22.02.2025.csv")

    # 2. Create the same environment
    #    Must match all parameters used in training: window_size, sl_options, tp_options
    test_env = ForexTradingEnv(
        df=test_df,
        window_size=30,         # same as training
        sl_options=[30, 60, 80],  
        tp_options=[30, 60, 80]
    )

    # Wrap in DummyVecEnv just like training
    vec_test_env = DummyVecEnv([lambda: test_env])

    # 3. Load the trained model
    #    Must match the file name you saved in train_agent.py
    model = PPO.load("model_eurusd", env=vec_test_env)

    # 4. Initialize logs
    obs = vec_test_env.reset()
    done = False

    # For equity tracking
    equity_curve = []

    # For trade tracking
    trade_history = []
    trade_id = 1  

    # 5. Step through environment until done
    while not done:
        # Predict action (deterministic or stochastic: 'deterministic=True' for consistent test)
        action, _states = model.predict(obs, deterministic=True)

        # Take a step in the environment
        obs, rewards, dones, info = vec_test_env.step(action)
        done = dones[0]  

        # Log the latest trade info from environment
        trade_info = vec_test_env.get_attr("last_trade_info")[0]
        if trade_info:
            # If a trade was taken (direction != None in your env),
            # trade_info['pnl'] = trade's profit/loss in pips (or 0 if no trade)
            trade_history.append({
                "Trade Number": trade_id,
                "Entry Price": trade_info["entry_price"],
                "Exit Price": trade_info["exit_price"],
                "Profit/Loss": trade_info["pnl"]
            })
            trade_id += 1  

        # Log equity
        current_equity = vec_test_env.get_attr("equity")[0]
        equity_curve.append(current_equity)

    # 6. Convert trades to DataFrame and save
    trades_df = pd.DataFrame(trade_history)
    output_file = "trade_history_output.csv"
    trades_df.to_csv(output_file, index=False)
    print(f"Trade history saved to {output_file}")

    # 7. Plot equity curve
    plt.figure(figsize=(10, 6))
    plt.plot(equity_curve, label='Equity (Test Data)')
    plt.title("Equity Curve - Single-Bar RL Environment Test")
    plt.xlabel("Time Steps")
    plt.ylabel("Equity")
    plt.legend()
    plt.show()

if __name__ == "__main__":
    main()