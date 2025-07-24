//+------------------------------------------------------------------+
//|                                                    GROK 3xAI     |
//|        Expert Advisor Multi-Conferma - MetaTrader 5 (MQL5)       |
//+------------------------------------------------------------------+
#property strict

#ifndef OP_BUY
#define OP_BUY 0
#endif
#ifndef OP_SELL
#define OP_SELL 1
#endif

input int SL_Pips = 30;
input double RR_Low = 2.0;
input double RR_High = 3.0;
input double Risk_Low = 2.5;
input double Risk_High = 20.0;
input double ATRMultiplier = 1.5;
input int    MaxTrades     = 3;  // limite operazioni aperte

// Variabili aggiornabili da Telegram
input double riskPercent   = 2.0; // percentuale di rischio predefinita
input int    takeProfitPips = 60; // TP iniziale in pips
input int    stopLossPips   = 30; // SL iniziale in pips

datetime lastTradeTime = 0;
double initialBalance, maxEquity;

int OnInit() {
    initialBalance = AccountInfoDouble(ACCOUNT_BALANCE);
    maxEquity = initialBalance;
    return(INIT_SUCCEEDED);
}


//+------------------------------------------------------------------+
//| Funzione per leggere il controllo da Telegram                    |
//+------------------------------------------------------------------+
bool IsEAEnabled()
{
   string status;
   int fileHandle = FileOpen("ea_control.txt", FILE_READ|FILE_ANSI);
   if (fileHandle != INVALID_HANDLE)
   {
      status = FileReadString(fileHandle);
      FileClose(fileHandle);
      status = StringTrim(status);
      if(status == "ACTIVE")
         return true;
   }
   return false;
}


//+------------------------------------------------------------------+
//| Gestione comandi avanzati da file Telegram                       |
//+------------------------------------------------------------------+
void CheckTelegramCommands()
{
   string command;
   int handle = FileOpen("ea_command.txt", FILE_READ|FILE_ANSI);
   if(handle != INVALID_HANDLE)
   {
      command = FileReadString(handle);
      FileClose(handle);
      command = StringTrim(command);

      if(command == "/emergency_stop")
      {
         CloseAllPositions();
         int h=FileOpen("ea_control.txt", FILE_WRITE|FILE_ANSI);
         if(h!=INVALID_HANDLE)
         {
            FileWriteString(h, "INACTIVE");
            FileClose(h);
         }
         Print("🔴 Emergency Stop attivato!");
      }
      else if(StringFind(command, "/set_risk") == 0)
      {
         double val = StringToDouble(StringSubstr(command, 10));
         riskPercent = val;
         Print("✅ Risk aggiornato: ", riskPercent);
      }
      else if(StringFind(command, "/set_tp") == 0)
      {
         double val = StringToDouble(StringSubstr(command, 8));
         takeProfitPips = (int)val;
         Print("✅ TakeProfit aggiornato: ", takeProfitPips);
      }
      else if(StringFind(command, "/set_sl") == 0)
      {
         double val = StringToDouble(StringSubstr(command, 8));
         stopLossPips = (int)val;
         Print("✅ StopLoss aggiornato: ", stopLossPips);
      }
   }
}

//+------------------------------------------------------------------+
//| Funzione per chiudere tutte le operazioni                        |
//+------------------------------------------------------------------+
void CloseAllPositions()
{
   for(int i=PositionsTotal()-1; i>=0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(!PositionClose(ticket))
         Print("❌ Errore chiusura posizione: ", ticket);
   }
}

void OnTick() {
    if(!IsEAEnabled())
        return;

    CheckTelegramCommands();

    if(!NewsFilter() || DailyDrawdownExceeded())
        return;

    if(!(Period()==PERIOD_M5 || Period()==PERIOD_M15))
        return;

    if(PositionsTotal() >= MaxTrades)
        return;

    if(!TimeFilter() || SpreadTooHigh() || !ATRCheck() || !TrendConfirmed() || (TimeCurrent() - lastTradeTime < 180))
        return;

    int confirmations = CheckConfirmations();
    double score = CalculateConfidenceScore();
    if(score < 50 || confirmations < 3)
        return;

    double stoploss = (stopLossPips * _Point) + ATRMultiplier * iATR(_Symbol, PERIOD_M5, 14, 0);
    double rr = 2.0;
    if(score >= 90)
        rr = 4.0;
    else if(score >= 70)
        rr = 3.0;
    double takeprofit = (takeProfitPips > 0) ? takeProfitPips * _Point : stoploss * rr;
    double risk = riskPercent;
    if(score >= 90)
        risk = MathMin(riskPercent*1.5, Risk_High);
    double lot = CalculateRiskLot(stoploss, risk);
    int direction = EntryDirection();

    double price = direction == 1 ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID);
    double sl = direction == 1 ? price - stoploss : price + stoploss;
    double tp = direction == 1 ? price + takeprofit : price - takeprofit;

    if(direction == 1)
        OrderSend(_Symbol, OP_BUY, lot, price, 10, sl, tp, "Buy", 0, 0, clrGreen);
    else if(direction == -1)
        OrderSend(_Symbol, OP_SELL, lot, price, 10, sl, tp, "Sell", 0, 0, clrRed);

    ManageRunnerTrade();

    lastTradeTime = TimeCurrent();
}

bool TimeFilter() {
    int hour = TimeHour(TimeCurrent());
    return (hour >= 8 && hour <= 22);
}

bool SpreadTooHigh() {
    double spread = (SymbolInfoDouble(_Symbol, SYMBOL_ASK) - SymbolInfoDouble(_Symbol, SYMBOL_BID)) / _Point;
    return spread > 50;
}

bool ATRCheck() {
    double atr_now = iATR(_Symbol, PERIOD_M5, 14, 0);
    double atr_avg = iATR(_Symbol, PERIOD_M5, 50, 0);
    return atr_now < (2.3 * atr_avg);
}

bool NewsFilter()
{
    int h = FileOpen("news_time.txt", FILE_READ|FILE_ANSI);
    if(h!=INVALID_HANDLE)
    {
        datetime t = (datetime)FileReadNumber(h);
        FileClose(h);
        if(MathAbs(TimeCurrent()-t) <= 900)
            return false;
    }
    return true;
}

bool DailyDrawdownExceeded()
{
    static double startEquity = 0;
    static datetime startTime = 0;

    if(TimeDay(startTime) != TimeDay(TimeCurrent()))
    {
        startTime = TimeCurrent();
        startEquity = AccountInfoDouble(ACCOUNT_EQUITY);
    }

    double equity = AccountInfoDouble(ACCOUNT_EQUITY);
    double dd = (startEquity - equity) / startEquity * 100.0;
    return dd > 20.0;
}

bool TrendConfirmed()
{
    double ema50 = iMA(_Symbol, PERIOD_H4, 50, 0, MODE_EMA, PRICE_CLOSE, 0);
    double ema200 = iMA(_Symbol, PERIOD_H4, 200, 0, MODE_EMA, PRICE_CLOSE, 0);
    double price = Close[0];
    if(ema50 > ema200 && price > ema50) return true;
    if(ema50 < ema200 && price < ema50) return true;
    return false;
}

bool IsStopHunt()
{
    double open1 = iOpen(_Symbol, PERIOD_M5, 1);
    double close1 = iClose(_Symbol, PERIOD_M5, 1);
    double high1 = iHigh(_Symbol, PERIOD_M5, 1);
    double low1  = iLow(_Symbol, PERIOD_M5, 1);

    double upper = high1 - MathMax(open1, close1);
    double lower = MathMin(open1, close1) - low1;
    double body  = MathAbs(close1 - open1);

    return ((upper > body*2 && close1 < open1) || (lower > body*2 && close1 > open1));
}

bool IsFailedBreakout()
{
    double high1 = iHigh(_Symbol, PERIOD_M5, 1);
    double high2 = iHigh(_Symbol, PERIOD_M5, 2);
    double low1  = iLow(_Symbol, PERIOD_M5, 1);
    double low2  = iLow(_Symbol, PERIOD_M5, 2);
    double close1 = iClose(_Symbol, PERIOD_M5, 1);

    bool hb = (high1 > high2) && (close1 < high2);
    bool lb = (low1 < low2)  && (close1 > low2);
    return hb || lb;
}

bool IsLiquidityPOI()
{
    double vol_now = iVolume(_Symbol, PERIOD_M5, 0);
    double vol_avg = (iVolume(_Symbol, PERIOD_M5,1)+iVolume(_Symbol, PERIOD_M5,2)+iVolume(_Symbol, PERIOD_M5,3))/3.0;
    double price = Close[0];
    double high = iHigh(_Symbol, PERIOD_H1, 1);
    double low  = iLow(_Symbol, PERIOD_H1, 1);
    bool near = (MathAbs(price-high) < 20*_Point) || (MathAbs(price-low) < 20*_Point);
    return (vol_now > vol_avg*1.5 && near);
}

int CheckConfirmations() {
    int conf = 0;

    // RSI
    double rsi = iRSI(_Symbol, PERIOD_M5, 14, PRICE_CLOSE, 0);
    if(rsi < 30 || rsi > 70) conf++;

    // EMA trend
    double ema20 = iMA(_Symbol, PERIOD_M5, 20, 0, MODE_EMA, PRICE_CLOSE, 0);
    double prev_close = iClose(_Symbol, PERIOD_M5, 1);
    if((prev_close <= ema20 && Close[0] > ema20) ||
       (prev_close >= ema20 && Close[0] < ema20))
        conf++;

    // ADX trend
    double adx = iADX(_Symbol, PERIOD_M5, 14, PRICE_CLOSE, MODE_MAIN, 0);
    if(adx > 25) conf++;

    // Volume spike
    if(iVolume(_Symbol, PERIOD_M5, 0) > 1.8 * iVolume(_Symbol, PERIOD_M5, 1)) conf++;

    // 4 EMA alignment
    double ema57 = iMA(_Symbol, PERIOD_M5, 57, 0, MODE_EMA, PRICE_CLOSE, 0);
    double ema114 = iMA(_Symbol, PERIOD_M5, 114, 0, MODE_EMA, PRICE_CLOSE, 0);
    double ema150 = iMA(_Symbol, PERIOD_M5, 150, 0, MODE_EMA, PRICE_CLOSE, 0);
    double ema214 = iMA(_Symbol, PERIOD_M5, 214, 0, MODE_EMA, PRICE_CLOSE, 0);
    if(ema57 < ema114 && ema114 < ema150 && ema150 < ema214) conf++;

    // Pivot breakout
    double pivot = (iHigh(NULL, PERIOD_D1, 1) + iLow(NULL, PERIOD_D1, 1) + iClose(NULL, PERIOD_D1, 1)) / 3;
    double R1 = 2 * pivot - iLow(NULL, PERIOD_D1, 1);
    double S1 = 2 * pivot - iHigh(NULL, PERIOD_D1, 1);
    if((Close[0] > R1 + 5 * _Point) || (Close[0] < S1 - 5 * _Point)) conf++;

    // Fibonacci level (approssimato con distanza % dal massimo/minimo giorno precedente)
    double high = iHigh(NULL, PERIOD_D1, 1);
    double low = iLow(NULL, PERIOD_D1, 1);
    double fib_382 = high - 0.382 * (high - low);
    double fib_618 = high - 0.618 * (high - low);
    if(Close[0] > fib_618 && Close[0] < fib_382) conf++;

    // Prossimità a livelli chiave (simulata)
    if(MathAbs(Close[0] - pivot) < 10 * _Point) conf++;

    return conf;
}

int EntryDirection() {
    double rsi = iRSI(_Symbol, PERIOD_M5, 14, PRICE_CLOSE, 0);
    if(rsi < 30) return 1;
    if(rsi > 70) return -1;
    return 0;
}

double CalculateRiskLot(double stop_loss, double risk_percent) {
    double risk_amount = AccountInfoDouble(ACCOUNT_BALANCE) * (risk_percent / 100.0);
    double lot = risk_amount / stop_loss / SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
    return NormalizeDouble(lot, 2);
}


void ManageRunnerTrade()
{
    for(int i = OrdersTotal() - 1; i >= 0; i--)
    {
        if(OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
        {
            if(OrderSymbol() == _Symbol && (OrderType() == OP_BUY || OrderType() == OP_SELL))
            {
                datetime opentime = OrderOpenTime();
                ENUM_TIMEFRAMES tf = (TimeCurrent() - opentime > 43200) ? PERIOD_H4 : PERIOD_CURRENT;
                if(tf != PERIOD_H4 && tf != PERIOD_D1)
                    continue;

                double open_price = OrderOpenPrice();
                double current_price = (OrderType() == OP_BUY) ? SymbolInfoDouble(_Symbol, SYMBOL_BID) : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
                double profit_pips = MathAbs(current_price - open_price) / _Point;

                double sl = OrderStopLoss();
                double new_sl;

                // BE: quando profitto supera 2x SL
                if(profit_pips >= SL_Pips * 2 && sl == 0)
                {
                    new_sl = (OrderType() == OP_BUY) ? open_price + (10 * _Point) : open_price - (10 * _Point);
                    OrderModify(OrderTicket(), OrderOpenPrice(), new_sl, OrderTakeProfit(), 0, clrBlue);
                }

                // Take Parziale a 3x SL
                if(profit_pips >= SL_Pips * 3 && OrderLots() >= 0.02)
                {
                    double partial = NormalizeDouble(OrderLots() / 2.0, 2);
                    int type = OrderType();
                    double price = (type == OP_BUY) ? SymbolInfoDouble(_Symbol, SYMBOL_BID) : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
                    OrderClose(OrderTicket(), partial, price, 5, clrRed);
                }

                // Trailing dopo 3x SL superato
                if(profit_pips >= SL_Pips * 3)
                {
                    double trail = SL_Pips * _Point;
                    new_sl = (OrderType() == OP_BUY) ? current_price - trail : current_price + trail;
                    if((OrderType() == OP_BUY && new_sl > sl) || (OrderType() == OP_SELL && new_sl < sl))
                        OrderModify(OrderTicket(), OrderOpenPrice(), new_sl, OrderTakeProfit(), 0, clrYellow);
                }

                // Uscita in caso di inversione forte (ADX < 20 e RSI opposto)
                double rsi = iRSI(_Symbol, tf, 14, PRICE_CLOSE, 0);
                double adx = iADX(_Symbol, tf, 14, PRICE_CLOSE, MODE_MAIN, 0);
                if(adx < 20 && ((OrderType() == OP_BUY && rsi < 40) || (OrderType() == OP_SELL && rsi > 60)))
                {
                    double price = (OrderType() == OP_BUY) ? SymbolInfoDouble(_Symbol, SYMBOL_BID) : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
                    OrderClose(OrderTicket(), OrderLots(), price, 5, clrViolet);
                }
            }
        }
    }
}

double CalculateConfidenceScore()
{
    double score = 0;

    // RSI estremo
    double rsi = iRSI(_Symbol, PERIOD_M5, 14, PRICE_CLOSE, 0);
    if(rsi < 18 || rsi > 82)
        score += 15;

    // ADX alto
    double adx = iADX(_Symbol, PERIOD_H1, 14, PRICE_CLOSE, MODE_MAIN, 0);
    if(adx > 28)
        score += 15;

    // EMA ben allineate
    double ema57 = iMA(_Symbol, PERIOD_M5, 57, 0, MODE_EMA, PRICE_CLOSE, 0);
    double ema114 = iMA(_Symbol, PERIOD_M5, 114, 0, MODE_EMA, PRICE_CLOSE, 0);
    double ema150 = iMA(_Symbol, PERIOD_M5, 150, 0, MODE_EMA, PRICE_CLOSE, 0);
    double ema214 = iMA(_Symbol, PERIOD_M5, 214, 0, MODE_EMA, PRICE_CLOSE, 0);
    if(ema57 > ema114 && ema114 > ema150 && ema150 > ema214)
        score += 15;

    // Volume spike
    double vol_now = iVolume(_Symbol, PERIOD_M5, 0);
    double vol_prev = iVolume(_Symbol, PERIOD_M5, 1);
    if(vol_now > vol_prev * 1.8)
        score += 10;

    // Supporti/resistenze, pivot (simulati)
    double s1 = iLow(_Symbol, PERIOD_D1, 0) - 100 * _Point;
    double r1 = iHigh(_Symbol, PERIOD_D1, 0) + 100 * _Point;
    double price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
    if(MathAbs(price - s1) < 30 * _Point || MathAbs(price - r1) < 30 * _Point)
        score += 10;

    // Order block presente (simulato)
    if(iClose(_Symbol, PERIOD_M5, 0) > iOpen(_Symbol, PERIOD_M5, 0) && iClose(_Symbol, PERIOD_M5, 1) < iOpen(_Symbol, PERIOD_M5, 1))
        score += 15;

    // Fibonacci 61.8% (simulato livello)
    double fib_level = iLow(_Symbol, PERIOD_H1, 1) + 0.618 * (iHigh(_Symbol, PERIOD_H1, 1) - iLow(_Symbol, PERIOD_H1, 1));
    if(MathAbs(price - fib_level) < 20 * _Point)
        score += 10;

    // Pitchfork key level (simulato)
    if(MathAbs(price - iMA(_Symbol, PERIOD_H1, 100, 0, MODE_EMA, PRICE_CLOSE, 0)) < 25 * _Point)
        score += 5;

    // Onde di Elliott (simulato se 3 candele a zigzag)
    double c1 = iClose(_Symbol, PERIOD_M5, 2);
    double c2 = iClose(_Symbol, PERIOD_M5, 1);
    double c3 = iClose(_Symbol, PERIOD_M5, 0);
    if((c1 < c2 && c2 > c3) || (c1 > c2 && c2 < c3))
        score += 5;

    // Elementi istituzionali
    if(IsStopHunt())
        score += 15;
    if(IsFailedBreakout())
        score += 15;
    if(IsLiquidityPOI())
        score += 10;
    if(IsCandlestickPatternConfirmed())
        score += 10;

    return score;
}


void CheckAndTrade()
{
    double score = CalculateConfidenceScore();
    double rr_ratio = 2.0; // default
    double lot = 0.01; // default lotto minimo

    // Skip se score < 50
    if(score < 50)
        return;

    // Aggiustamento dinamico lotto e R:R
    if(score >= 50 && score < 70)
    {
        rr_ratio = 2.0;
        lot = 0.01;
    }
    else if(score >= 70 && score < 90)
    {
        rr_ratio = 3.0;
        lot = 0.01 + 0.005; // aumenta leggermente
    }
    else if(score >= 90)
    {
        rr_ratio = 4.0;
        lot = 0.02; // lotto massimo consentito per 100€ iniziali
    }

    // Calcolo direzione trade (semplificato su RSI)
    double rsi = iRSI(_Symbol, PERIOD_M5, 14, PRICE_CLOSE, 0);
    int trade_type = -1;

    if(rsi < 18)
        trade_type = OP_BUY;
    else if(rsi > 82)
        trade_type = OP_SELL;
    else
        return;

    // Prezzo corrente
    double price = (trade_type == OP_BUY) ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID);

    // StopLoss e TakeProfit dinamici
    double atr = iATR(_Symbol, PERIOD_M5, 14, 0);
    double sl_pips = atr * 1.5;
    double tp_pips = sl_pips * rr_ratio;

    double sl = (trade_type == OP_BUY) ? price - sl_pips : price + sl_pips;
    double tp = (trade_type == OP_BUY) ? price + tp_pips : price - tp_pips;

    // Invio ordine
    int ticket = OrderSend(_Symbol, trade_type, lot, price, 3, sl, tp, "AutoTrade by Confidence", 0, 0, clrBlue);
    if(ticket < 0)
        Print("Errore apertura ordine: ", GetLastError());
    else
        Print("Ordine aperto con score: ", score, " R:R: ", rr_ratio, " Lotto: ", lot);
}


bool IsBullishEngulfing()
{
    double open1 = iOpen(_Symbol, PERIOD_M5, 1);
    double close1 = iClose(_Symbol, PERIOD_M5, 1);
    double open0 = iOpen(_Symbol, PERIOD_M5, 0);
    double close0 = iClose(_Symbol, PERIOD_M5, 0);

    return (close1 < open1 && close0 > open0 && close0 > open1 && open0 < close1);
}

bool IsBearishEngulfing()
{
    double open1 = iOpen(_Symbol, PERIOD_M5, 1);
    double close1 = iClose(_Symbol, PERIOD_M5, 1);
    double open0 = iOpen(_Symbol, PERIOD_M5, 0);
    double close0 = iClose(_Symbol, PERIOD_M5, 0);

    return (close1 > open1 && close0 < open0 && close0 < open1 && open0 > close1);
}

bool IsPinBar()
{
    double open = iOpen(_Symbol, PERIOD_M5, 0);
    double close = iClose(_Symbol, PERIOD_M5, 0);
    double high = iHigh(_Symbol, PERIOD_M5, 0);
    double low = iLow(_Symbol, PERIOD_M5, 0);

    double body = MathAbs(close - open);
    double range = high - low;

    return (body < (range * 0.25)); // corpo molto piccolo
}


bool IsCandlestickPatternConfirmed()
{
    return (IsBullishEngulfing() || IsBearishEngulfing() || IsPinBar());
}

bool RequirePatternConfirmation(double score, ENUM_TIMEFRAMES tf)
{
    // Per operazioni in H4/D1 runner, il pattern è obbligatorio se score < 80
    if((tf == PERIOD_H4 || tf == PERIOD_D1) && score < 80)
        return true;

    // Se score è alto, il pattern può essere bypassato
    return false;
}

