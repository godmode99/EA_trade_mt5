#pragma once

#include <Trade\Trade.mqh>

bool DetectFalseBreakSetup(const string symbol,const ENUM_TIMEFRAMES timeframe,const double riskReward,const double prevDayRangePoints)
  {
   return(false);
  }

void SubmitFalseBreakOrder(const string symbol,const ENUM_TIMEFRAMES timeframe,const double volume,const double riskReward,const int slippagePoints)
  {
  }

double GetPreviousDayRangePoints(const string symbol,const int utcOffsetHours)
  {
   return(0.0);
  }
