# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/10/21 19:56
describe: 择时交易策略样例
"""
import pandas as pd
from loguru import logger
from collections import OrderedDict
from czsc import signals
from czsc.connectors import qmt_connector as qmc
from czsc.traders import CzscAdvancedTrader
from czsc.objects import Freq, Operate, Signal, Factor, Event, RawBar, PositionLong, PositionShort

logger.disable('czsc.signals.cxt')


# 定义择时交易策略，策略函数名称必须是 trader_strategy
# ----------------------------------------------------------------------------------------------------------------------
def trader_strategy(symbol):
    """5日线"""

    def get_signals(cat: CzscAdvancedTrader) -> OrderedDict:
        s = OrderedDict({"symbol": cat.symbol, "dt": cat.end_dt, "close": cat.latest_price})
        s.update(signals.bar_operate_span_V221111(cat.kas['15分钟'], k1='全天', span=('0935', '1450')))
        s.update(signals.bar_operate_span_V221111(cat.kas['15分钟'], k1='临收盘', span=('1410', '1450')))
        s.update(signals.bar_operate_span_V221111(cat.kas['15分钟'], k1='下午', span=('1300', '1450')))
        s.update(signals.bar_operate_span_V221111(cat.kas['15分钟'], k1='上午', span=('0935', '1130')))
        s.update(signals.bar_zdt_V221111(cat, '15分钟', di=1))
        s.update(signals.bar_end_V221111(cat.kas['5分钟'], '15分钟'))
        s.update(signals.bar_mean_amount_V221112(cat.kas['日线'], di=2, n=20, th1=2, th2=1000))

        signals.update_ma_cache(cat.kas["日线"], ma_type='SMA', timeperiod=5)
        s.update(signals.tas_ma_base_V221101(cat.kas["日线"], di=1, ma_type='SMA', timeperiod=5))
        s.update(signals.tas_ma_base_V221101(cat.kas["日线"], di=2, ma_type='SMA', timeperiod=5))
        s.update(signals.tas_ma_base_V221101(cat.kas["日线"], di=5, ma_type='SMA', timeperiod=5))
        c = cat.kas['30分钟']
        s.update(signals.cxt_first_buy_V221126(c, di=1))
        return s

    # 定义多头持仓对象和交易事件
    long_pos = PositionLong(symbol, hold_long_a=1, hold_long_b=1, hold_long_c=1,
                            T0=False, long_min_interval=3600 * 4)
    long_events = [
        Event(name="开多", operate=Operate.LO,
              signals_not=[Signal('15分钟_D1K_涨跌停_涨停_任意_任意_0')],
              signals_all=[
                  Signal("日线_D2K20B均额_2至1000千万_是_任意_任意_0"),
                  Signal("15分钟_K线_结束_是_任意_任意_0"),
              ],
              factors=[
                  Factor(name="站上SMA5", signals_all=[
                      Signal("全天_0935_1450_是_任意_任意_0"),
                      Signal("日线_D1K_SMA5_多头_任意_任意_0"),
                      Signal("日线_D5K_SMA5_空头_向下_任意_0"),
                      Signal('30分钟_D1B_BUY1_一买_任意_任意_0'),
                  ]),
              ]),

        Event(name="平多", operate=Operate.LE,
              signals_not=[Signal('15分钟_D1K_涨跌停_跌停_任意_任意_0')],
              factors=[
                  Factor(name="跌破SMA5", signals_all=[
                      Signal("下午_1300_1450_是_任意_任意_0"),
                      Signal("日线_D1K_SMA5_空头_任意_任意_0"),
                      Signal("日线_D2K_SMA5_多头_任意_任意_0"),
                  ]),
              ]),
    ]

    tactic = {
        "base_freq": '5分钟',
        "freqs": ['15分钟', '30分钟', '日线'],
        "get_signals": get_signals,

        "long_pos": long_pos,
        "long_events": long_events,
    }

    return tactic


# 定义命令行接口的特定参数
# ----------------------------------------------------------------------------------------------------------------------
# 【必须】执行结果路径
results_path = r"D:\ts_data\SMA5_测试2"

# 【必须】策略回测参数设置
dummy_params = {
    "symbols": qmc.get_symbols('train'),  # 回测使用的标的列表
    "sdt": "20150101",  # K线数据开始时间
    "mdt": "20200101",  # 策略回测开始时间
    "edt": "20220101",  # 策略回测结束时间
}

# 【可选】策略回放参数设置
replay_params = {
    "symbol": qmc.get_symbols('check')[0],  # 回放交易品种
    "sdt": "20150101",  # K线数据开始时间
    "mdt": "20200101",  # 策略回放开始时间
    "edt": "20220101",  # 策略回放结束时间
}

# 【可选】是否使用 debug 模式输出更多信息
debug = True


# 【必须】定义K线数据读取函数，这里是为了方便接入任意数据源的K线行情
# ----------------------------------------------------------------------------------------------------------------------

def read_bars(symbol, sdt, edt):
    """自定义K线数据读取函数，便于接入任意来源的行情数据进行回测一类的分析

    :param symbol: 标的名称
    :param sdt: 行情开始时间
    :param edt: 行情介绍时间
    :return: list of RawBar
    """
    sdt = pd.to_datetime(sdt).strftime("%Y%m%d")
    edt = pd.to_datetime(edt).strftime("%Y%m%d")
    df = qmc.get_local_kline(symbol, period='5m', start_time=sdt, end_time=edt, dividend_type='back',
                             data_dir=r"D:\迅投极速策略交易系统交易终端 华鑫证券QMT实盘\datadir", update=True)
    bars = qmc.format_stock_kline(df, Freq.F5)
    return bars
