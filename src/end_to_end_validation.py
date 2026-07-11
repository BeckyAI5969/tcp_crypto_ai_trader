from pathlib import Path

from src.execution_engine import ExecutionEngine


def configure_test_logs(engine: ExecutionEngine) -> Path:
    test_log_dir = Path("logs") / "e2e_validation"
    test_log_dir.mkdir(parents=True, exist_ok=True)

    paper_trader = engine.router.paper_trader

    paper_trader.logger.log_dir = test_log_dir
    paper_trader.logger.trade_csv = (
        test_log_dir / "paper_trade_log.csv"
    )
    paper_trader.logger.trade_jsonl = (
        test_log_dir / "paper_trade_log.jsonl"
    )

    paper_trader.paper_report.log_dir = test_log_dir
    paper_trader.paper_report.report_file = (
        test_log_dir / "paper_report.json"
    )

    paper_trader.risk_report.log_dir = test_log_dir
    paper_trader.risk_report.report_file = (
        test_log_dir / "risk_report.json"
    )

    return test_log_dir


def require(condition: bool, message: str):
    if not condition:
        raise RuntimeError(message)


def main():
    print("=" * 72)
    print("SPRINT 15 END-TO-END VALIDATION")
    print("=" * 72)

    engine = ExecutionEngine(
        execution_mode="PAPER",
        signal_validity_minutes=15,
    )

    test_log_dir = configure_test_logs(engine)

    symbol = "BTCUSDT"
    signal_price = 60000.0
    atr = 300.0
    strategy_score = 95.0

    print("\n[1/5] Creating 15m signal")

    signal_event = engine.on_15m_signal(
        symbol=symbol,
        signal="BUY",
        score=strategy_score,
        signal_price=signal_price,
        atr=atr,
    )

    print(signal_event.to_dict())

    require(
        signal_event.action == "QUEUE",
        "15m signal was not added to queue",
    )

    print("\n[2/5] Confirming with 5m data")

    confirmation_event = engine.on_5m_close(
        symbol=symbol,
        ema20=60020.0,
        ema50=59800.0,
        macd=120.0,
        macd_signal=80.0,
        rsi14=58.0,
        volume=1500.0,
        volume_ma20=1000.0,
    )

    print(confirmation_event.to_dict())

    require(
        confirmation_event.action == "CONFIRM",
        "5m confirmation did not pass",
    )

    print("\n[3/5] Triggering 1m entry")

    entry_event = engine.on_1m_close(
        symbol=symbol,
        current_price=60010.0,
        ema20=60000.0,
        ema50=59920.0,
        rsi14=57.0,
        macd=35.0,
        macd_signal=20.0,
    )

    print(entry_event.to_dict())

    require(
        entry_event.action == "EXECUTE",
        "1m entry was not executed",
    )

    position = (
        engine.router.paper_trader
        .portfolio
        .find_open_position(symbol)
    )

    require(
        position is not None,
        "Paper position was not opened",
    )

    require(
        position.stop_loss is not None,
        "Stop loss was not assigned",
    )

    require(
        position.take_profit is not None,
        "Take profit was not assigned",
    )

    require(
        position.quantity > 0,
        "Position quantity is invalid",
    )

    print("\nOPEN POSITION")
    print(position.to_dict())

    print("\n[4/5] Updating position with tick price")

    update_price = position.entry_price + (
        position.entry_price - position.stop_loss
    )

    update_event = engine.on_tick(
        symbol=symbol,
        price=update_price,
    )

    print(update_event.to_dict())

    require(
        update_event.action == "UPDATE",
        "Tick position update failed",
    )

    position = (
        engine.router.paper_trader
        .portfolio
        .find_open_position(symbol)
    )

    require(
        position is not None,
        "Position closed before take profit test",
    )

    require(
        position.stop_loss >= position.entry_price,
        "Break-even stop was not activated",
    )

    print("\nPOSITION AFTER BREAK-EVEN")
    print(position.to_dict())

    print("\n[5/5] Closing position at take profit")

    close_event = engine.on_tick(
        symbol=symbol,
        price=position.take_profit,
    )

    print(close_event.to_dict())

    require(
        close_event.action == "CLOSE",
        "Position did not close at take profit",
    )

    summary = engine.summary()
    portfolio = summary["portfolio"]

    require(
        portfolio["open_positions"] == 0,
        "Open position remains after close",
    )

    require(
        portfolio["closed_positions"] == 1,
        "Closed position was not recorded",
    )

    require(
        portfolio["realized_pnl"] > 0,
        "Realized profit was not calculated",
    )

    required_files = [
        test_log_dir / "paper_trade_log.csv",
        test_log_dir / "paper_trade_log.jsonl",
        test_log_dir / "paper_report.json",
        test_log_dir / "risk_report.json",
    ]

    for file_path in required_files:
        require(
            file_path.exists(),
            f"Required report was not created: {file_path}",
        )

    print("\n" + "=" * 72)
    print("END-TO-END VALIDATION: PASS")
    print("=" * 72)
    print("15m Signal       : PASS")
    print("5m Confirmation  : PASS")
    print("1m Entry         : PASS")
    print("Risk Approval    : PASS")
    print("Paper Execution  : PASS")
    print("Break-even       : PASS")
    print("Take Profit Exit : PASS")
    print("Realized PnL     : PASS")
    print("Trade Logging    : PASS")
    print("Reports          : PASS")
    print()
    print("Portfolio Summary:")
    print(portfolio)
    print()
    print("Validation logs:")
    print(test_log_dir)


if __name__ == "__main__":
    main()