#pragma once

struct RangeScanResult
  {
   double high;
   double low;
   int    bars;
  };

namespace RangeScanner
  {
   bool ScanM15HighLow(const string symbol,const datetime from,const datetime to,double &outHigh,double &outLow,int &outBars)
     {
      outHigh = 0.0;
      outLow = 0.0;
      outBars = 0;

      if(symbol == NULL || StringLen(symbol) == 0)
         return(false);

      if(from > to)
         return(false);

      MqlRates rates[];
      ArraySetAsSeries(rates,false);

      int copied = CopyRates(symbol,PERIOD_M15,from,to,rates);
      if(copied <= 0)
         return(false);

      outHigh = rates[0].high;
      outLow = rates[0].low;

      for(int i=1;i<copied;++i)
        {
         if(rates[i].high > outHigh)
            outHigh = rates[i].high;
         if(rates[i].low < outLow)
            outLow = rates[i].low;
        }

      outBars = copied;
      return(true);
     }
  }
