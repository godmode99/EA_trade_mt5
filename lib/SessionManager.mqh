#pragma once

bool GetPrevDayWindowUTC3(const string symbol, datetime &dayStart, datetime &dayEnd)
  {
   dayStart = 0;
   dayEnd = 0;

   if(symbol == NULL || StringLen(symbol) == 0)
      return(false);

   const int bars_to_scan = 400; // little more than 3 days of M15 bars
   datetime times[];
   ArraySetAsSeries(times,false);

   int copied = CopyTime(symbol,PERIOD_M15,0,bars_to_scan,times);
   if(copied <= 0)
      return(false);

   const int utc_offset_seconds = 3 * 3600;

   MqlDateTime dt;
   TimeToStruct(times[0] + utc_offset_seconds,dt);
   int currentDayKey = dt.year * 10000 + dt.mon * 100 + dt.day;

   int prevDayKey = -1;
   datetime prevFirst = 0;

   for(int i=0;i<copied;++i)
     {
      TimeToStruct(times[i] + utc_offset_seconds,dt);
      int dayKey = dt.year * 10000 + dt.mon * 100 + dt.day;

      if(dayKey == currentDayKey)
         continue;

      if(prevDayKey == -1)
        {
         prevDayKey = dayKey;
         prevFirst = times[i];
         continue;
        }

      if(dayKey != prevDayKey)
         break;

      prevFirst = times[i];
     }

   if(prevDayKey == -1)
      return(false);

   MqlDateTime prevStartStruct;
   TimeToStruct(prevFirst + utc_offset_seconds,prevStartStruct);
   prevStartStruct.hour = 0;
   prevStartStruct.min = 0;
   prevStartStruct.sec = 0;

   datetime prevStartUTC3 = StructToTime(prevStartStruct);
   dayStart = prevStartUTC3 - utc_offset_seconds;
   dayEnd = dayStart + 86400 - 1;

   return(true);
  }
