"""Evaluating Prophet model on M4 timeseries

"""

from darts import TimeSeries
from darts.models import Prophet
from darts.metrics import mape, mase
from darts.backtesting import backtest_forecasting, backtest_gridsearch, forecasting_residuals
from darts.backtesting.backtesting import explore_models
from darts.utils.statistics import check_seasonality, remove_seasonality, extract_trend_and_seasonality

import numpy as np
import pandas as pd
from tqdm import tqdm
import pickle as pkl

from M4_metrics import *


if __name__ == "__main__":

    data_categories = ['Yearly', 'Quarterly', 'Monthly', 'Weekly', 'Daily', 'Hourly']

    info_dataset = pd.read_csv('dataset/M4-info.csv', delimiter=',').set_index('M4id')

    for cat in data_categories[::-1]:
        # Load TimeSeries from M4
        ts_train = pkl.load(open("dataset/train_"+cat+".pkl", "rb"))
        ts_test = pkl.load(open("dataset/test_"+cat+".pkl", "rb"))

        # Test models on all time series
        mase_all = []
        smape_all = []
        m = info_dataset.Frequency[cat[0]+"1"]
        for train, test in tqdm(zip(ts_train, ts_test)):
            train_des = train
            seasonOut = 1
            if m > 1:
                if check_seasonality(train, m=int(m), max_lag=2*m):
                    pass
                else:
                    m = 1
            try:
                prophet_args = {
                                'daily_seasonality': False,
                                'weekly_seasonality': False,
                                'yearly_seasonality': False,
                                'frequency': None,
                                }
                if cat == 'Daily':
                    prophet_args['daily_seasonality'] = True
                    prophet_args['changepoint_range'] = 0.95
                elif cat == 'Hourly':
                    prophet_args['daily_seasonality'] = True
                elif cat == 'Weekly':
                    prophet_args['weekly_seasonality'] = True
                    prophet_args['changepoint_range'] = 0.95
                elif cat == 'Monthly':
                    prophet_args['yearly_seasonality'] = True
                elif cat == 'Quarterly':
                    prophet_args['yearly_seasonality'] = True
                elif cat == 'Yearly':
                    prophet_args['yearly_seasonality'] = True
                prophet = Prophet(**prophet_args)
                derivate = np.diff(train.values(), n=1)
                jump = derivate.max()/(train.max()-train.min())
                try:
                    if jump <= 0.5:
                        prophet.fit(train)
                    else:
                        prophet.fit(train.drop_before(train.time_index()[np.argmax(derivate)+1]))
                except ValueError:
                    continue
                forecast_prophet = prophet.predict(len(test))
                m = info_dataset.Frequency[cat[0]+"1"]
                mase_all.append(np.vstack([
                    mase_m4(train, test, forecast_prophet, m=m),
                    ]))
                smape_all.append(np.vstack([
                    smape_m4(test, forecast_prophet),
                    ]))
            except Exception as e:
                print(e)
                pkl.dump(mase_all, open("prophet_mase_"+cat+".pkl", "wb"))
                pkl.dump(smape_all, open("prophet_smape_"+cat+".pkl", "wb"))
                break
        pkl.dump(mase_all, open("prophet_mase_"+cat+".pkl", "wb"))
        pkl.dump(smape_all, open("prophet_smape_"+cat+".pkl", "wb"))
        print("MASE; Prophet: {}".format(*tuple(np.nanmean(np.stack(mase_all), axis=(0, 2)))))
        print("sMAPE; Prophet: {}".format(*tuple(np.nanmean(np.stack(smape_all), axis=(0, 2)))))
        print("OWA: ", OWA_m4(cat, np.nanmean(np.stack(smape_all), axis=(0, 2)),
                              np.nanmean(np.stack(mase_all), axis=(0, 2))))
