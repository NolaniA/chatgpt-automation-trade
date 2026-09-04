//+------------------------------------------------------------------+
//|                                                         stop.mq5 |
//|                                  Copyright 2025, MetaQuotes Ltd. |
//|                                             https://www.mql5.com |
//+------------------------------------------------------------------+

// Description:
// Hedge Recovery EA using Candle Close + Profit + Distance.
// - Opens BUY STOP and SELL STOP around market price.
// - Recovery direction is decided from the last CLOSED candle (prices[1]).
// - BUY recovery requires BUY-side profit >= MinRecoveryProfit and
//   candle close above the BUY anchor by RecoveryStepPoint.
// - SELL recovery requires SELL-side profit >= MinRecoveryProfit and
//   candle close below the SELL anchor by RecoveryStepPoint.
// - The latest recovery price becomes the next anchor.
// - BUY and SELL Recovery use separate anchors and can switch direction.
// - Designed for MT5 Hedging accounts.

#property copyright "Copyright 2025, MetaQuotes Ltd."
#property link      "https://www.mql5.com"
#property version   "1.30"
#property description "Hedge Recovery EA: Candle Close + Profit + Distance"
#property description "Uses prices[1] close, profit threshold and recovery distance."
#property description "BUY and SELL recovery can switch direction using separate anchors."

#include <Trade/Trade.mqh>

CTrade trade;

//==================================================================
// GLOBAL INPUT
//==================================================================

input int CandleRate = 10;

input double LotSize = 0.01;

input int DistancePoint = 1500;

input int SlippagePoint = 20;

input ulong Magic = 10001;

input int TrendBars = 3;

input int TrendStartShift = 3;

// กำไรรวมของ Basket ที่ต้องถึงก่อน Close All
input double BasketTargetProfit = 1.0;

// กำไรรวมขั้นต่ำของฝั่งที่จะเริ่ม/เพิ่ม Recovery
input double MinRecoveryProfit = 1.0;

// ระยะขั้นต่ำจาก Anchor ถึงราคาปิดของแท่งล่าสุด (Point)
input int RecoveryStepPoint = 500;

// จำนวน Recovery สูงสุดต่อ Basket
input int MaxRecoveryPositions = 5;


//==================================================================
// GLOBAL
//==================================================================

MqlRates prices[];

int PendingBuy = 0;
int PendingSell = 0;

int PositionBuy = 0;
int PositionSell = 0;

// Anchor ของ Recovery แต่ละฝั่งแยกจากกัน
// 0 = ยังไม่มี Recovery ฝั่งนั้น
double LastRecoveryBuyPrice = 0;
double LastRecoverySellPrice = 0;

// ป้องกันเปิด Recovery ซ้ำจากแท่งปิดเดียวกัน
datetime LastRecoverySignalBarTime = 0;


//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   //===============================================================
   // EA นี้ต้องใช้ Hedging Account
   //===============================================================
   ENUM_ACCOUNT_MARGIN_MODE marginMode =
      (ENUM_ACCOUNT_MARGIN_MODE)AccountInfoInteger(
         ACCOUNT_MARGIN_MODE
      );


   if(marginMode != ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)
   {
      Print(
         "INIT FAILED | EA requires HEDGING account"
      );

      return INIT_FAILED;
   }


   //===============================================================
   // TRADE SETTINGS
   //===============================================================
   trade.SetExpertMagicNumber(Magic);

   trade.SetMarginMode();

   trade.SetDeviationInPoints(
      SlippagePoint
   );

   trade.SetTypeFillingBySymbol(
      _Symbol
   );


   return INIT_SUCCEEDED;
}


//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{

}


//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   //===============================================================
   // LOAD PRICE
   //===============================================================
   if(!LoadPrices(CandleRate))
      return;


   //===============================================================
   // LOAD CURRENT STATE
   //===============================================================
   LoadTradeState();


   //===============================================================
   // CLOSE
   // ถ้ามีทั้ง BUY + SELL ให้ปิด Position ที่กำไรมากที่สุด
   //===============================================================
   // CloseBestProfitPosition();
   ManageRecovery();


   //===============================================================
   // REFRESH STATE
   // เพราะอาจมี Position ถูกปิด
   //===============================================================
   LoadTradeState();


   //===============================================================
   // OPEN
   //===============================================================
   OpenBuyStop();

   OpenSellStop();


   //===============================================================
   // REFRESH STATE
   // เพราะอาจมี Pending Order ถูกเปิดใหม่
   //===============================================================
   LoadTradeState();


   //===============================================================
   // MODIFY
   //===============================================================
   ModifyBuyStop();

   ModifySellStop();
}


//+------------------------------------------------------------------+
//| Load Prices                                                      |
//+------------------------------------------------------------------+
bool LoadPrices(const int candle)
{
   ArraySetAsSeries(
      prices,
      true
   );


   int minimumBars =
      TrendStartShift +
      TrendBars +
      1;


   int requiredBars =
      MathMax(
         candle,
         minimumBars
      );


   int copied =
      CopyRates(
         _Symbol,
         _Period,
         0,
         requiredBars,
         prices
      );


   if(copied < requiredBars)
   {
      Print(
         "CopyRates failed",
         " | copied=", copied,
         " | required=", requiredBars
      );

      return false;
   }


   return true;
}


//+------------------------------------------------------------------+
//| Load Trade State                                                 |
//+------------------------------------------------------------------+
void LoadTradeState()
{
   //===============================================================
   // RESET
   //===============================================================
   PendingBuy = 0;
   PendingSell = 0;

   PositionBuy = 0;
   PositionSell = 0;


   //===============================================================
   // PENDING ORDERS
   //===============================================================
   for(int i = 0; i < OrdersTotal(); i++)
   {
      ulong ticket =
         OrderGetTicket(i);


      if(ticket == 0)
         continue;


      if(
         OrderGetString(ORDER_SYMBOL)
         !=
         _Symbol
      )
         continue;


      if(
         (ulong)OrderGetInteger(ORDER_MAGIC)
         !=
         Magic
      )
         continue;


      ENUM_ORDER_TYPE type =
         (ENUM_ORDER_TYPE)OrderGetInteger(
            ORDER_TYPE
         );


      if(type == ORDER_TYPE_BUY_STOP)
      {
         PendingBuy++;
      }
      else
      if(type == ORDER_TYPE_SELL_STOP)
      {
         PendingSell++;
      }
   }


   //===============================================================
   // POSITIONS
   //===============================================================
   for(int i = 0; i < PositionsTotal(); i++)
   {
      ulong ticket =
         PositionGetTicket(i);


      if(ticket == 0)
         continue;


      if(
         PositionGetString(POSITION_SYMBOL)
         !=
         _Symbol
      )
         continue;


      if(
         (ulong)PositionGetInteger(POSITION_MAGIC)
         !=
         Magic
      )
         continue;


      ENUM_POSITION_TYPE type =
         (ENUM_POSITION_TYPE)PositionGetInteger(
            POSITION_TYPE
         );


      if(type == POSITION_TYPE_BUY)
      {
         PositionBuy++;
      }
      else
      if(type == POSITION_TYPE_SELL)
      {
         PositionSell++;
      }
   }
}


//+------------------------------------------------------------------+
//| Get Safe Distance Point                                          |
//+------------------------------------------------------------------+
int GetDistancePoint()
{
   int stopLevel =
      (int)SymbolInfoInteger(
         _Symbol,
         SYMBOL_TRADE_STOPS_LEVEL
      );


   int freezeLevel =
      (int)SymbolInfoInteger(
         _Symbol,
         SYMBOL_TRADE_FREEZE_LEVEL
      );


   int brokerMinimum =
      MathMax(
         stopLevel,
         freezeLevel
      );


   int distance =
      MathMax(
         DistancePoint,
         brokerMinimum + 1
      );


   return distance;
}


//+------------------------------------------------------------------+
//| Normalize Buy Stop Price                                         |
//+------------------------------------------------------------------+
double NormalizeBuyPrice(double price)
{
   double tickSize =
      SymbolInfoDouble(
         _Symbol,
         SYMBOL_TRADE_TICK_SIZE
      );


   if(tickSize <= 0)
      return NormalizeDouble(price, _Digits);


   price =
      MathCeil(
         price / tickSize
      ) * tickSize;


   return NormalizeDouble(
      price,
      _Digits
   );
}


//+------------------------------------------------------------------+
//| Normalize Sell Stop Price                                        |
//+------------------------------------------------------------------+
double NormalizeSellPrice(double price)
{
   double tickSize =
      SymbolInfoDouble(
         _Symbol,
         SYMBOL_TRADE_TICK_SIZE
      );


   if(tickSize <= 0)
      return NormalizeDouble(price, _Digits);


   price =
      MathFloor(
         price / tickSize
      ) * tickSize;


   return NormalizeDouble(
      price,
      _Digits
   );
}


//+------------------------------------------------------------------+
//| Check Trade Result                                               |
//+------------------------------------------------------------------+
bool IsTradeSuccess()
{
   uint retcode =
      trade.ResultRetcode();


   return(
      retcode == TRADE_RETCODE_DONE ||
      retcode == TRADE_RETCODE_PLACED ||
      retcode == TRADE_RETCODE_DONE_PARTIAL ||
      retcode == TRADE_RETCODE_NO_CHANGES
   );
}


//+------------------------------------------------------------------+
//| Open Buy Stop                                                    |
//+------------------------------------------------------------------+
void OpenBuyStop()
{
   if(
      PendingBuy != 0 ||
      PositionBuy != 0
   )
      return;


   double ask =
      SymbolInfoDouble(
         _Symbol,
         SYMBOL_ASK
      );


   if(ask <= 0)
      return;


   int distancePoint =
      GetDistancePoint();


   double price =
      NormalizeBuyPrice(
         ask +
         (
            distancePoint *
            _Point
         )
      );


   bool requestResult =
      trade.BuyStop(
         LotSize,
         price,
         _Symbol,
         0,
         0
      );


   if(
      !requestResult ||
      !IsTradeSuccess()
   )
   {
      Print(
         "BUY STOP FAILED",
         " | Price=", price,
         " | Retcode=", trade.ResultRetcode(),
         " | ", trade.ResultRetcodeDescription()
      );

      return;
   }


   Print(
      "BUY STOP OPEN",
      " | Ticket=", trade.ResultOrder(),
      " | Price=", price,
      " | Ask=", ask,
      " | Distance=", distancePoint
   );
}


//+------------------------------------------------------------------+
//| Open Sell Stop                                                   |
//+------------------------------------------------------------------+
void OpenSellStop()
{
   if(
      PendingSell != 0 ||
      PositionSell != 0
   )
      return;


   double bid =
      SymbolInfoDouble(
         _Symbol,
         SYMBOL_BID
      );


   if(bid <= 0)
      return;


   int distancePoint =
      GetDistancePoint();


   double price =
      NormalizeSellPrice(
         bid -
         (
            distancePoint *
            _Point
         )
      );


   bool requestResult =
      trade.SellStop(
         LotSize,
         price,
         _Symbol,
         0,
         0
      );


   if(
      !requestResult ||
      !IsTradeSuccess()
   )
   {
      Print(
         "SELL STOP FAILED",
         " | Price=", price,
         " | Retcode=", trade.ResultRetcode(),
         " | ", trade.ResultRetcodeDescription()
      );

      return;
   }


   Print(
      "SELL STOP OPEN",
      " | Ticket=", trade.ResultOrder(),
      " | Price=", price,
      " | Bid=", bid,
      " | Distance=", distancePoint
   );
}


//+------------------------------------------------------------------+
//| Modify Buy Stop                                                  |
//+------------------------------------------------------------------+
void ModifyBuyStop()
{
   if(
      PendingBuy == 0 ||
      PositionBuy != 0
   )
      return;


   double ask =
      SymbolInfoDouble(
         _Symbol,
         SYMBOL_ASK
      );


   if(ask <= 0)
      return;


   int distancePoint =
      GetDistancePoint();


   for(int i = 0; i < OrdersTotal(); i++)
   {
      ulong ticket =
         OrderGetTicket(i);


      if(ticket == 0)
         continue;


      if(
         OrderGetString(ORDER_SYMBOL)
         !=
         _Symbol
      )
         continue;


      if(
         (ulong)OrderGetInteger(ORDER_MAGIC)
         !=
         Magic
      )
         continue;


      ENUM_ORDER_TYPE type =
         (ENUM_ORDER_TYPE)OrderGetInteger(
            ORDER_TYPE
         );


      if(type != ORDER_TYPE_BUY_STOP)
         continue;


      double oldPrice =
         OrderGetDouble(
            ORDER_PRICE_OPEN
         );


      double distance =
         (oldPrice - ask)
         /
         _Point;


      // ราคาเคลื่อนลงหนี BUY STOP เกินระยะที่กำหนด
      // ให้เลื่อน BUY STOP ลงมาตามราคา
      if(distance > distancePoint)
      {
         double newPrice =
            NormalizeBuyPrice(
               ask +
               (
                  distancePoint *
                  _Point
               )
            );


         // ป้องกัน Modify ราคาเดิม
         if(
            MathAbs(
               newPrice - oldPrice
            ) < (_Point / 2.0)
         )
            continue;


         bool requestResult =
            trade.OrderModify(
               ticket,
               newPrice,
               0,
               0,
               ORDER_TIME_GTC,
               0,
               0
            );


         if(
            !requestResult ||
            !IsTradeSuccess()
         )
         {
            Print(
               "MODIFY BUY STOP FAILED",
               " | Ticket=", ticket,
               " | Old=", oldPrice,
               " | New=", newPrice,
               " | Distance=", distance,
               " | Retcode=", trade.ResultRetcode(),
               " | ", trade.ResultRetcodeDescription()
            );

            continue;
         }


         Print(
            "MODIFY BUY STOP",
            " | Ticket=", ticket,
            " | Old=", oldPrice,
            " | New=", newPrice,
            " | Ask=", ask,
            " | Distance=", distance
         );
      }
   }
}


//+------------------------------------------------------------------+
//| Modify Sell Stop                                                 |
//+------------------------------------------------------------------+
void ModifySellStop()
{
   if(
      PendingSell == 0 ||
      PositionSell != 0
   )
      return;


   double bid =
      SymbolInfoDouble(
         _Symbol,
         SYMBOL_BID
      );


   if(bid <= 0)
      return;


   int distancePoint =
      GetDistancePoint();


   for(int i = 0; i < OrdersTotal(); i++)
   {
      ulong ticket =
         OrderGetTicket(i);


      if(ticket == 0)
         continue;


      if(
         OrderGetString(ORDER_SYMBOL)
         !=
         _Symbol
      )
         continue;


      if(
         (ulong)OrderGetInteger(ORDER_MAGIC)
         !=
         Magic
      )
         continue;


      ENUM_ORDER_TYPE type =
         (ENUM_ORDER_TYPE)OrderGetInteger(
            ORDER_TYPE
         );


      if(type != ORDER_TYPE_SELL_STOP)
         continue;


      double oldPrice =
         OrderGetDouble(
            ORDER_PRICE_OPEN
         );


      double distance =
         (bid - oldPrice)
         /
         _Point;


      // ราคาเคลื่อนขึ้นหนี SELL STOP เกินระยะที่กำหนด
      // ให้เลื่อน SELL STOP ขึ้นมาตามราคา
      if(distance > distancePoint)
      {
         double newPrice =
            NormalizeSellPrice(
               bid -
               (
                  distancePoint *
                  _Point
               )
            );


         // ป้องกัน Modify ราคาเดิม
         if(
            MathAbs(
               newPrice - oldPrice
            ) < (_Point / 2.0)
         )
            continue;


         bool requestResult =
            trade.OrderModify(
               ticket,
               newPrice,
               0,
               0,
               ORDER_TIME_GTC,
               0,
               0
            );


         if(
            !requestResult ||
            !IsTradeSuccess()
         )
         {
            Print(
               "MODIFY SELL STOP FAILED",
               " | Ticket=", ticket,
               " | Old=", oldPrice,
               " | New=", newPrice,
               " | Distance=", distance,
               " | Retcode=", trade.ResultRetcode(),
               " | ", trade.ResultRetcodeDescription()
            );

            continue;
         }


         Print(
            "MODIFY SELL STOP",
            " | Ticket=", ticket,
            " | Old=", oldPrice,
            " | New=", newPrice,
            " | Bid=", bid,
            " | Distance=", distance
         );
      }
   }
}


//+------------------------------------------------------------------+
//| Close Position ที่กำไรมากที่สุด                                  |
//+------------------------------------------------------------------+
bool CloseBestProfitPosition()
{
   // ต้องมีทั้ง BUY และ SELL
   if(
      PositionBuy == 0 ||
      PositionSell == 0
   )
      return false;


   ulong bestTicket = 0;

   double bestProfit = 0;


   //===============================================================
   // FIND BEST PROFIT POSITION
   //===============================================================
   for(int i = 0; i < PositionsTotal(); i++)
   {
      ulong ticket =
         PositionGetTicket(i);


      if(ticket == 0)
         continue;


      if(
         PositionGetString(POSITION_SYMBOL)
         !=
         _Symbol
      )
         continue;


      if(
         (ulong)PositionGetInteger(POSITION_MAGIC)
         !=
         Magic
      )
         continue;


      double profit =
         PositionGetDouble(
            POSITION_PROFIT
         );


      // ปิดเฉพาะ Position ที่กำไรมากกว่า 0
      if(profit <= bestProfit)
         continue;


      bestProfit = profit;

      bestTicket = ticket;
   }


   if(bestTicket == 0)
      return false;


   //===============================================================
   // CLOSE
   //===============================================================
   bool requestResult =
      trade.PositionClose(
         bestTicket,
         SlippagePoint
      );


   if(
      !requestResult ||
      !IsTradeSuccess()
   )
   {
      Print(
         "CLOSE BEST POSITION FAILED",
         " | Ticket=", bestTicket,
         " | Profit=", bestProfit,
         " | Retcode=", trade.ResultRetcode(),
         " | ", trade.ResultRetcodeDescription()
      );

      return false;
   }


   Print(
      "CLOSE BEST POSITION",
      " | Ticket=", bestTicket,
      " | Profit=", bestProfit
   );


   return true;
}


//+------------------------------------------------------------------+
//| Close All Positions                                              |
//+------------------------------------------------------------------+
void CloseAllPositions()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket =
         PositionGetTicket(i);


      if(ticket == 0)
         continue;


      if(
         PositionGetString(POSITION_SYMBOL)
         !=
         _Symbol
      )
         continue;


      if(
         (ulong)PositionGetInteger(POSITION_MAGIC)
         !=
         Magic
      )
         continue;


      bool result =
         trade.PositionClose(
            ticket,
            SlippagePoint
         );


      if(
         !result ||
         !IsTradeSuccess()
      )
      {
         Print(
            "CLOSE FAILED",
            " | Ticket=", ticket,
            " | Retcode=", trade.ResultRetcode(),
            " | ",
            trade.ResultRetcodeDescription()
         );
      }
      else
      {
         Print(
            "POSITION CLOSED",
            " | Ticket=", ticket
         );
      }
   }
}

//+------------------------------------------------------------------+
//| Open Recovery Sell                                               |
//+------------------------------------------------------------------+
bool OpenRecoverySell()
{
   bool result =
      trade.Sell(
         LotSize,
         _Symbol,
         0,
         0,
         0,
         "Recovery SELL"
      );


   if(
      !result ||
      !IsTradeSuccess()
   )
   {
      Print(
         "RECOVERY SELL FAILED",
         " | Retcode=", trade.ResultRetcode(),
         " | ",
         trade.ResultRetcodeDescription()
      );

      return false;
   }


   Print(
      "RECOVERY SELL",
      " | Lot=", LotSize,
      " | Price=", trade.ResultPrice()
   );


   return true;
}

//+------------------------------------------------------------------+
//| Open Recovery Buy                                                |
//+------------------------------------------------------------------+
bool OpenRecoveryBuy()
{
   bool result =
      trade.Buy(
         LotSize,
         _Symbol,
         0,
         0,
         0,
         "Recovery BUY"
      );


   if(
      !result ||
      !IsTradeSuccess()
   )
   {
      Print(
         "RECOVERY BUY FAILED",
         " | Retcode=", trade.ResultRetcode(),
         " | ",
         trade.ResultRetcodeDescription()
      );

      return false;
   }


   Print(
      "RECOVERY BUY",
      " | Lot=", LotSize,
      " | Price=", trade.ResultPrice()
   );


   return true;
}

//+------------------------------------------------------------------+
//| Manage Hedge Recovery                                            |
//|                                                                  |
//| LOGIC: Candle Close + Profit + Distance                          |
//|                                                                  |
//| TWO-WAY RECOVERY                                                 |
//| - BUY และ SELL Recovery เปิดสลับกันได้                           |
//| - ไม่มี RecoveryDirection Lock                                   |
//| - BUY และ SELL มี Anchor แยกกัน                                  |
//| - ใช้เฉพาะ prices[1].close = แท่งที่ปิดแล้ว                      |
//| - 1 Closed Candle เปิด Recovery ได้สูงสุด 1 Position              |
//|                                                                  |
//| BUY RECOVERY                                                     |
//| - buyProfit >= MinRecoveryProfit                                 |
//| - Close[1] >= BuyAnchor + RecoveryStepPoint                      |
//|                                                                  |
//| SELL RECOVERY                                                    |
//| - sellProfit >= MinRecoveryProfit                                |
//| - Close[1] <= SellAnchor - RecoveryStepPoint                     |
//|                                                                  |
//| ANCHOR                                                           |
//| - ถ้ายังไม่มี Recovery ฝั่งนั้น ใช้ Weighted Average Entry       |
//| - ถ้ามี Recovery แล้ว ใช้ราคา Recovery ล่าสุดของฝั่งนั้น         |
//|                                                                  |
//| EXIT                                                             |
//| - totalProfit >= BasketTargetProfit -> CloseAllPositions()        |
//+------------------------------------------------------------------+
void ManageRecovery()
{
   double buyProfit = 0;
   double sellProfit = 0;
   double totalProfit = 0;

   int buyCount = 0;
   int sellCount = 0;

   int recoveryBuyCount = 0;
   int recoverySellCount = 0;

   double buyVolume = 0;
   double sellVolume = 0;

   double buyOpenValue = 0;
   double sellOpenValue = 0;

   long latestRecoveryBuyTime = 0;
   long latestRecoverySellTime = 0;

   double latestRecoveryBuyPrice = 0;
   double latestRecoverySellPrice = 0;


   //===============================================================
   // CALCULATE BASKET
   //===============================================================
   for(int i = 0; i < PositionsTotal(); i++)
   {
      ulong ticket = PositionGetTicket(i);

      if(ticket == 0)
         continue;

      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;

      if((ulong)PositionGetInteger(POSITION_MAGIC) != Magic)
         continue;


      ENUM_POSITION_TYPE type =
         (ENUM_POSITION_TYPE)PositionGetInteger(
            POSITION_TYPE
         );

      double profit =
         PositionGetDouble(
            POSITION_PROFIT
         );

      double volume =
         PositionGetDouble(
            POSITION_VOLUME
         );

      double openPrice =
         PositionGetDouble(
            POSITION_PRICE_OPEN
         );

      string comment =
         PositionGetString(
            POSITION_COMMENT
         );

      long positionTime =
         PositionGetInteger(
            POSITION_TIME_MSC
         );


      totalProfit += profit;


      //============================================================
      // BUY
      //============================================================
      if(type == POSITION_TYPE_BUY)
      {
         buyProfit += profit;
         buyCount++;

         buyVolume += volume;
         buyOpenValue += openPrice * volume;


         if(StringFind(comment, "Recovery BUY") >= 0)
         {
            recoveryBuyCount++;

            if(positionTime > latestRecoveryBuyTime)
            {
               latestRecoveryBuyTime = positionTime;
               latestRecoveryBuyPrice = openPrice;
            }
         }
      }


      //============================================================
      // SELL
      //============================================================
      else
      if(type == POSITION_TYPE_SELL)
      {
         sellProfit += profit;
         sellCount++;

         sellVolume += volume;
         sellOpenValue += openPrice * volume;


         if(StringFind(comment, "Recovery SELL") >= 0)
         {
            recoverySellCount++;

            if(positionTime > latestRecoverySellTime)
            {
               latestRecoverySellTime = positionTime;
               latestRecoverySellPrice = openPrice;
            }
         }
      }
   }


   //===============================================================
   // ต้องมีทั้ง BUY และ SELL ก่อน
   //===============================================================
   if(
      buyCount == 0 ||
      sellCount == 0
   )
   {
      LastRecoveryBuyPrice = 0;
      LastRecoverySellPrice = 0;
      LastRecoverySignalBarTime = 0;

      return;
   }


   //===============================================================
   // BASKET TARGET -> CLOSE ALL
   //===============================================================
   if(totalProfit >= BasketTargetProfit)
   {
      Print(
         "BASKET TARGET",
         " | Total=", totalProfit,
         " | BuyProfit=", buyProfit,
         " | SellProfit=", sellProfit
      );


      CloseAllPositions();


      LastRecoveryBuyPrice = 0;
      LastRecoverySellPrice = 0;
      LastRecoverySignalBarTime = 0;

      return;
   }


   //===============================================================
   // RECOVERY LIMIT
   //===============================================================
   int recoveryPositions =
      recoveryBuyCount +
      recoverySellCount;


   if(recoveryPositions >= MaxRecoveryPositions)
      return;


   if(RecoveryStepPoint <= 0)
      return;


   if(ArraySize(prices) < 2)
      return;


   if(
      buyVolume <= 0 ||
      sellVolume <= 0
   )
      return;


   //===============================================================
   // LAST CLOSED CANDLE
   //===============================================================
   double candleClose =
      prices[1].close;


   datetime signalBarTime =
      prices[1].time;


   //===============================================================
   // 1 CLOSED CANDLE = MAX 1 RECOVERY
   //===============================================================
   if(
      LastRecoverySignalBarTime != 0 &&
      LastRecoverySignalBarTime == signalBarTime
   )
      return;


   //===============================================================
   // ORIGINAL WEIGHTED AVERAGE ENTRY
   //===============================================================
   double originalBuyAnchor =
      buyOpenValue /
      buyVolume;


   double originalSellAnchor =
      sellOpenValue /
      sellVolume;


   //===============================================================
   // RESTORE BUY / SELL ANCHOR AFTER EA RESTART
   //===============================================================
   if(
      LastRecoveryBuyPrice <= 0 &&
      latestRecoveryBuyPrice > 0
   )
   {
      LastRecoveryBuyPrice =
         latestRecoveryBuyPrice;
   }


   if(
      LastRecoverySellPrice <= 0 &&
      latestRecoverySellPrice > 0
   )
   {
      LastRecoverySellPrice =
         latestRecoverySellPrice;
   }


   //===============================================================
   // SEPARATE ANCHORS
   //===============================================================
   double buyAnchor =
      LastRecoveryBuyPrice > 0
      ?
      LastRecoveryBuyPrice
      :
      originalBuyAnchor;


   double sellAnchor =
      LastRecoverySellPrice > 0
      ?
      LastRecoverySellPrice
      :
      originalSellAnchor;


   //===============================================================
   // DISTANCE FROM EACH ANCHOR
   //===============================================================
   double buyDistance =
      (candleClose - buyAnchor)
      /
      _Point;


   double sellDistance =
      (sellAnchor - candleClose)
      /
      _Point;


   //===============================================================
   // SIGNALS
   //===============================================================
   bool buySignal =
      buyProfit >= MinRecoveryProfit &&
      buyDistance >= RecoveryStepPoint;


   bool sellSignal =
      sellProfit >= MinRecoveryProfit &&
      sellDistance >= RecoveryStepPoint;


   //===============================================================
   // BUY ONLY
   //===============================================================
   if(
      buySignal &&
      !sellSignal
   )
   {
      if(OpenRecoveryBuy())
      {
         LastRecoveryBuyPrice =
            trade.ResultPrice();

         LastRecoverySignalBarTime =
            signalBarTime;


         Print(
            "RECOVERY BUY EXECUTED",
            " | Close=", candleClose,
            " | Anchor=", buyAnchor,
            " | Distance=", buyDistance,
            " | BuyProfit=", buyProfit,
            " | SellProfit=", sellProfit,
            " | Basket=", totalProfit,
            " | RecoveryBuyCount=", recoveryBuyCount + 1,
            " | RecoverySellCount=", recoverySellCount,
            " | NewBuyAnchor=", LastRecoveryBuyPrice
         );
      }

      return;
   }


   //===============================================================
   // SELL ONLY
   //===============================================================
   if(
      sellSignal &&
      !buySignal
   )
   {
      if(OpenRecoverySell())
      {
         LastRecoverySellPrice =
            trade.ResultPrice();

         LastRecoverySignalBarTime =
            signalBarTime;


         Print(
            "RECOVERY SELL EXECUTED",
            " | Close=", candleClose,
            " | Anchor=", sellAnchor,
            " | Distance=", sellDistance,
            " | BuyProfit=", buyProfit,
            " | SellProfit=", sellProfit,
            " | Basket=", totalProfit,
            " | RecoveryBuyCount=", recoveryBuyCount,
            " | RecoverySellCount=", recoverySellCount + 1,
            " | NewSellAnchor=", LastRecoverySellPrice
         );
      }

      return;
   }


   //===============================================================
   // BOTH SIGNALS
   // Anchor อาจไขว้กันหลังจาก Recovery หลายรอบ
   // จึงเลือกฝั่งที่ทะลุ RecoveryStepPoint มากกว่า
   //===============================================================
   if(
      buySignal &&
      sellSignal
   )
   {
      double buyExcess =
         buyDistance -
         RecoveryStepPoint;


      double sellExcess =
         sellDistance -
         RecoveryStepPoint;


      if(buyExcess > sellExcess)
      {
         if(OpenRecoveryBuy())
         {
            LastRecoveryBuyPrice =
               trade.ResultPrice();

            LastRecoverySignalBarTime =
               signalBarTime;


            Print(
               "RECOVERY BUY EXECUTED",
               " | Mode=BOTH_SIGNAL_BUY_STRONGER",
               " | Close=", candleClose,
               " | BuyDistance=", buyDistance,
               " | SellDistance=", sellDistance,
               " | BuyProfit=", buyProfit,
               " | SellProfit=", sellProfit,
               " | NewBuyAnchor=", LastRecoveryBuyPrice
            );
         }
      }
      else
      if(sellExcess > buyExcess)
      {
         if(OpenRecoverySell())
         {
            LastRecoverySellPrice =
               trade.ResultPrice();

            LastRecoverySignalBarTime =
               signalBarTime;


            Print(
               "RECOVERY SELL EXECUTED",
               " | Mode=BOTH_SIGNAL_SELL_STRONGER",
               " | Close=", candleClose,
               " | BuyDistance=", buyDistance,
               " | SellDistance=", sellDistance,
               " | BuyProfit=", buyProfit,
               " | SellProfit=", sellProfit,
               " | NewSellAnchor=", LastRecoverySellPrice
            );
         }
      }


      return;
   }
}

