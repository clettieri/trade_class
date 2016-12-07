"""
This class is not meant to be used but rather to show at a conceptual level how a trade class may
be implemented.  The specifics of your system will differ greatly depending on the nature
of your trading system, your broker, and the order management needs you have.

This trade class is structured in that it receives price information in the form of
ticks or price bars from a main script.

It also requires the use of an OrderClass which contains information of pending orders
that your broker would then use to place your order.  This OrderClass would need to be tailored
specifically for your broker.  The account object would then contain such information as how
to connect with your broker.

This script is incomplete and broken, it is meant as a conceptual overview of how you could
implement a class for managing trades.
"""
import OrderClass #Class where order objects are implemented
from abc import ABCMeta, abstractmethod
import time as TIME #As TIME so as not to confuse with datetime
import random
import datetime

class Trade(object):
	'''
	This is the parent class of two child classes which offer different exit variations.
	The parameters I suggest are:
		account - Account object, something that has your connection to your broker, buying power, etc.
		position_object - Something that manages your open positions, will let you know what positions you have
		symbol - String for the symbol you wish to tade
		side - String as either "long" or "short", can be changed to a magic string
		qty - Size of trade, number of shares
		long_entry/ short_entry - Floats that represent your entry price, both included incase its a pending breakout trade
		long_protective_stop/ short_protective - Floats that represent your exit price

	'''

    __metaclass__ = ABCMeta
    
    def __init__(self, account, position_object, symbol, side, qty, 
                 long_entry=0.0, short_entry=0.0, long_protective_stop=0.0,
                 short_protective_stop=0.0, order_info=""):
        self.account = account
        self.position_object = position_obj
        self.symbol = symbol 
        self.order_info = order_info
        self.side = side.lower()
		#Check that the string for side is valid
        if self.side != "long" and self.side != "short":
            raise ValueError('side specified must be "long", "short"')
        self.qty = qty 
        self.long_entry = long_entry
        self.short_entry = short_entry
        self.long_protective_stop = long_protective_stop
        self.short_protective_stop = short_protective_stop
		#Warn if no stop price provided
        if self.long_protective_stop == 0.0 and self.short_protective_stop == 0.0:
            raise ValueError('NO STOP PRICE PROVIDED!!')
        self.order_list = []
        self.closed = False 
        self.sent_stop_order = False #Flag to only send stop order once
        self.entry_triggered = False  #Flag to know entry triggered
        self.place_entry_orders() #Function that actually sends the orders to your broker
        
        print "ORDER INFO FROM TRADE CLASS: " + self.order_info  #Debugging

    def place_entry_orders(self):
        '''(None) -> None
		
		This function requires your OrderClass implementation and self.account
		connect to your broker.  This function essentially builds the OrderClass
		object that we will send.  For information on an OrderClass object
		see the README.
		'''
        sym = self.symbol
        qty = self.qty
        if self.side == "long":
            #Place Long Entry Order
            print self.symbol + " trade object placing entry LONG at: " + str(self.long_entry) + " StopLoss: " + str(self.long_protective_stop)
			#Build OrderClass object
            entry_order = OrderClass(self.account, sym, qty, 0, OrderClass.Side_Buy, OrderClass.Type_Stop, self.long_entry + 0.05, "LongEntry" + self.order_info)
            entry_order.set_stop_order_detail(self.long_entry+buff, OrderClass.StopTriggerType_Print, OrderClass.StopType_Synthetic)
			#Send the order to your broker
            self.set_and_place_order(entry_order)
        
        if self.side == "short":
            #Place Short Entry Order
            print self.symbol + " trade object placing entry SHORT at: " + str(self.short_entry) + " StopLoss: " + str(self.short_protective_stop)
            #Build OrderClass object
			entry_order = OrderClass(conn, self.account, sym, qty, 0, OrderClass.Side_Sell, OrderClass.Type_Stop, self.short_entry - 0.05, "ShortEntry" + self.order_info)
            entry_order.set_stop_order_detail(self.short_entry-buff, OrderClass.StopTriggerType_Print, OrderClass.StopType_Synthetic)
            #Send the order to your broker
			self.set_and_place_order(entry_order)
            
    def update_protective_stop(self, stop_price):
        '''(float) -> None
		
		Will update the trade object's stop price.  Useful for trailing stops.
		'''
        if self.side == "long":
            self.long_protective_stop = stop_price
        elif self.side == "short":
            self.short_protective_stop = stop_price
        else:
            pass
            
    def set_and_place_order(self, order):
        '''(OrderClass) -> None
		
		Will take the OrderClass object and actually send the
		order to your broker.  Also will setup a tracking function
		so the status events of that order can be received.
		'''
		#Ensure valid comment for easier tracking on order updates
        valid_order_notes = ['LongEntry', 'ShortEntry', 'LongStop', 'ShortStop', 'ShortTP', 'LongTP'] #User defined
        valid_note = False
        for valid in valid_order_notes:
            if order.notes.startswith(valid):
                valid_note = True
        if not valid_note:
            print "MAJOR ERROR - INVALID ORDER NOTE: " + order.notes
		#Redundant check in case sent multiple orders
        if self.closed == True:
            print "Can't Place Order, Trade closed: " + str(order.notes)
            return
		#Redundant check in case sent multiple orders
        for pending_o in self.order_list:
            if pending_o.notes == order.notes:
                print "DUPLICATE ORDER TRYING TO BE PLACED " + str(self.trade_id)
                return
		#Place order, track all orders in this script, subscribe to update function
        self.order_list.append(order)
        order.place()
        order.on_update = self.order_update
            
    def cancel_pending_entry_orders(self):
        '''(None) -> None
		
		Loops through order list to cancel any marked entry.
		Useful for cancelling pending trades at end of day, etc.
		'''
        for o in self.order_list:
            if o.notes.startswith("LongEntry") or o.notes.startswith("ShortEntry"):
                o.cancel()
                
    def new_tick(self, last_print_obj):
        '''(TickObject) -> None
		
		This function receives updates from the main script with each current
		new tick.  Here we check if our trade is stopped out and send the exit
		order if True.
		'''		
		#Safety check - if trade closed, shouldn't be doing anything with new tick
        if self.closed == True:
            #waiting for main script to receive position update, to remove trade object
            print "Trade is closed, but in new tick function: " + str(self.symbol)
			
		#New Tick
        tick_price = last_print_obj.price
        
        #If not triggered entry, but stop reached - cancel pending entry
        if self.entry_triggered == False:
            if self.side == "long" and tick_price <= self.long_protective_stop:
                print "Stop reached before entry triggered, cancel LONG entry"
                self.cancel_pending_entry_orders()
            if self.side == "short" and tick_price >= self.short_protective_stop:
                print "Stop reached before entry triggered, cancel SHORT entry"
                self.cancel_pending_entry_orders()
        
        #Have Position for this trade still, Check if Stopped out
        if self.side == "long":
            if tick_price <= self.long_protective_stop and not self.sent_stop_order:
                print "NEW TICK - STOPPED OUT of LONG!"
                trade_size = min(self.position_object.size, self.qty)
                order = OrderClass(self.account, self.symbol, trade_size, 0 , OrderClass.Side_Sell, OrderClass.Type_Market, 0.0, 'LongStop' + self.order_info)
                self.sent_stop_order = True
                self.set_and_place_order(order)
        if self.side == "short":
            if tick_price >= self.short_protective_stop and not self.sent_stop_order:
                print "NEW TICK - STOPPED OUT of SHORT!"
                trade_size = min(abs(self.position_object.size), self.qty) #position objects return negative size
                order = OrderClass(self.account, self.symbol, trade_size, 0 , OrderClass.Side_Buy, OrderClass.Type_Market, 0.0, 'ShortStop' + self.order_info)
                self.sent_stop_order = True
                self.set_and_place_order(order)
 
    @abstractmethod
    def order_update(self, order):
        pass
    
    @abstractmethod
    def new_bar(self, bar_list):
        pass

    




"""###############################"""
"""### 	Child Classes of Trade ###"""
"""###############################"""

class TP_Trade(Trade):
	'''
	TP Trade 
	Will exit at a "Take Profit" price (TP).

	Additional parameters:
	tp_info - Float for the price you wish to take profits.  Will close position here with profit.
	'''
    
    def __init__(self, account, position_obj, symbol, side, qty,
                 long_entry=0.0, short_entry=0.0, long_protective_stop=0.0,
                 short_protective_stop=0.0, tp_price=0.0, order_info=""):
        Trade.__init__(self, account, position_obj, symbol, side, qty,
                 long_entry, short_entry,long_protective_stop, short_protective_stop, order_info)
        self.tp_price = tp_price
        print "TRADE INFO--- ID:%s  SIZE:%d EntryPrice:%f  TPPrice:%f" % (self.trade_id, self.qty, max(self.long_entry,self.short_entry), self.tp_price)
        
    def place_tp_order(self):
        '''(None) -> None
		
		Will build the OrderClass object and then call our function to send
		the order to the broker and track it in this script.
		'''
        if self.side == "long":
            #Long, place offer with tp price, LongTP
            tp_order = OrderClass(self.account, self.symbol, self.qty, self.qty, OrderClass.Side_Sell, OrderClass.Type_Limit, self.tp_price, notes="LongTP")
            self.set_and_place_order(tp_order)
        if self.side == "short":
            #Short, place bid with tp price, ShortTP
            tp_order = OrderClass(self.account, self.symbol, self.qty, self.qty, OrderClass.Side_Buy, OrderClass.Type_Limit, self.tp_price, notes="ShortTP")
            self.set_and_place_order(tp_order)
            
    def cancel_pending_TP_orders(self):
        '''(None) -> None
		
		Will loop through the order list and cancel any order
		with LongTP or ShortTP in the notes.
		'''
        for o in self.order_list:
            if o.notes == "LongTP" or o.notes == "ShortTP":
                o.cancel()
                print "CANCEL TP FUNC CALLED: " + str(self.trade_id) + " " + str(datetime.datetime.now().strftime("%H:%M:%S:"))
        
    def order_update(self, order):
        '''(order_obj) -> None
        
        Takes OrderClass object that is subsrcibed to for updates.
        All Entry and Stop orders MUST - have userinfo that begins with
        LongEntry/ ShortEntry or LongStop/ ShortStop for this to work.
		This function acts as your position manager and is called every time
		your order provides an updated event.
        '''
        print "STATUS:" + order.status_to_string(order.status) + " ID:" + str(self.trade_id) + " NOTES:" + str(order.notes) + " " + str(datetime.datetime.now().strftime("%H:%M:%S:"))
        #Order is filled
		if order.status == OrderClass.Status_Filled:
            print "ORDER FILLED: " + str(order.notes)  + "ID: " + str(self.trade_id)+ " " + str(datetime.datetime.now().strftime("%H:%M:%S:"))          
            self.order_list.remove(order) #Remove as pending order
            if order.notes.startswith("LongEntry") or order.notes.startswith("ShortEntry"):
                self.cancel_pending_entry_orders() #Cancel pending entry orders for this stock since in position
                self.entry_triggered = True
                self.place_tp_order()
            if order.notes.startswith("LongStop") or order.notes.startswith("ShortStop"):
                print "Stop Loss Filled - Trade Closed" + " ID: " + str(self.trade_id) 
                self.closed = True
                self.cancel_pending_TP_orders() #Stopped out so cancel pending take profit orders
            if order.notes == "LongTP" or order.notes == "ShortTP":
                print "TP Filled - Trade Closed" + " ID: " + str(self.trade_id) 
                self.closed = True 
                TIME.sleep(1)
		#Order is cancelled
        elif order.status == OrderClass.Status_Canceled:
            self.order_list.remove(order)
            if self.closed == False and (order.notes.startswith("LongStop") or order.notes.startswith("ShortStop")):
                print "@#$ STOP FOR TP CANCELLED - Trade not closed - replace tp stop" + " ID: " + str(self.trade_id) + " " + str(datetime.datetime.now().strftime("%H:%M:%S:"))
            if self.closed == False and (order.notes == "LongTP" or order.notes == "ShortTP"):
                print "@#$ TP Cancelled - but Trade not closed - replace" + " ID: " + str(self.trade_id) + " " + str(datetime.datetime.now().strftime("%H:%M:%S:"))
            if order.notes.startswith("LongEntry") or order.notes.startswith("ShortEntry"):
                if not self.entry_triggered:
                    print "Trade Not Triggered, Closing" + " ID: " + str(self.trade_id) + " " + str(datetime.datetime.now().strftime("%H:%M:%S:"))
                    self.closed = True
                else:
                    print "####Attempted to cancel entry but trade was triggered already"
		#Order is rejected
        elif order.status == OrderClass.Status_Rejected:
            print "ORDER REJECTED" + " ID: " + str(self.trade_id) 
            self.order_list.remove(order)
            if order.notes.startswith("LongStop") or order.notes.startswith("ShortStop"):
                self.sent_stop_order = False
            if order.notes.startswith("ShortEntry"):
                print "Is the stock CB? " + str(order.symbol)
		#Order receives partial fill
        elif order.status == OrderClass.Status_Partial:
            print "Partial Fill - " + order.symbol + " - " + order.notes + " -shares executed: " + str(order.executed_size)
        


class Trail_Trade(Trade):
	'''
	Trail Trade 
	Will exit with a trailing stop based on previous price bars.

	Additional parameters:
	trail_exit_bars - Integer, number of bars used for trailing exit
	stop_multiple_ITM_before_trail - How far in the money must the trade be before trailing, as function of stop size
    '''
	
    def __init__(self, account, position_obj, symbol, side, qty,
                 long_entry=0.0, short_entry=0.0, long_protective_stop=0.0,
                 short_protective_stop=0.0, trail_exit_bars=0, order_info=""):
        Trade.__init__(self, account, position_obj, symbol, side, qty,
                 long_entry, short_entry, long_protective_stop,
                 short_protective_stop, order_info)
        self.trail_exit_bars = trail_exit_bars
        self.trade_open_for_bars = 0 #assists trail bar exit
        self.stop_multiple_ITM_before_trail = 2 #multiple of stop size need to be ITM before trail kicks in
        self.can_trail_now = False #used so will only trail when multiple from stop
        
    def update_trailing_stop(self, bar_list):
        '''(list of time_bars) -> None
		
		Updates the trailing stop.  Finds the new stop price, then will place order.
		This function is only called when the minimum number of bars has closed, before
		trailing begins.
		'''
        n = self.trail_exit_bars
        if self.position_object.size == 0:
            print "CANT UPDATE TRAILING STOP, TRADE IS FLAT"
            print "Trade closed from update trail stop function:" + str(self.closed)
            return
        
		#Get the new stop price
        if self.side == "long":
            #find the lowest low of past n bars
            lowest_low = float("inf")
            for i in range(-1, -n-1, -1): #loop says start with -1 loop to -n (inclusive since barlist isclosed bars, count backwards)
                if bar_list[i]['low'] < lowest_low:
                    lowest_low = bar_list[i]['low']
            
            #update stop dictionary with the new stop price
            print "New Long Trailing Stop = " + str(lowest_low)
            self.long_protective_stop = lowest_low
        if self.side == "short":
            #find the highest high of past n bars
            highest_high = 0.0
            for i in range(-1, -n-1, -1):
                if bar_list[i]['high'] > highest_high:
                    highest_high = bar_list[i]['high']    
            #update stop dictionary with the new stop price
            print "New Short Trailing Stop = " + str(highest_high)
            self.short_protective_stop = highest_high


    def order_update(self, order):
        '''(order_obj) -> None
		
        Takes OrderClass object that is subsrcibed to for updates.
        All Entry and Stop orders MUST - have userinfo that begins with
        LongEntry/ ShortEntry or LongStop/ ShortStop for this to work.
		
		This function acts as your position manager and is called every time
		your order provides an updated event.
        '''
        print "STATUS:" + order.status_to_string(order.status) + " ID:" + str(self.trade_id) + " NOTES:" + str(order.notes) + " " + str(datetime.datetime.now().strftime("%H:%M:%S:"))
        #Order is filled
	    if order.status == OrderClass.Status_Filled:
            print "ORDER FILLED: " + str(order.notes)  + "ID: " + str(self.trade_id)+ " " + str(datetime.datetime.now().strftime("%H:%M:%S:"))          
            self.order_list.remove(order)
            if order.notes.startswith("LongEntry") or order.notes.startswith("ShortEntry"):
                self.cancel_pending_entry_orders()
                self.entry_triggered = True
            if order.notes.startswith("LongStop") or order.notes.startswith("ShortStop"):
                print "Stop Loss Filled - Trade Closed" + " ID: " + str(self.trade_id) 
                self.closed = True
		#Order is cancelled
        elif order.status == OrderClass.Status_Canceled:
            self.order_list.remove(order)
            if self.closed == False and (order.notes.startswith("LongStop") or order.notes.startswith("ShortStop")):
                print "@#$ STOP FOR TP CANCELLED - Trade not closed - replace tp stop" + " ID: " + str(self.trade_id) + " " + str(datetime.datetime.now().strftime("%H:%M:%S:"))
            if order.notes.startswith("LongEntry") or order.notes.startswith("ShortEntry"):
                if not self.entry_triggered:
                    print "Trade Not Triggered, Closing" + " ID: " + str(self.trade_id) + " " + str(datetime.datetime.now().strftime("%H:%M:%S:"))
                    self.closed = True
                else:
                    print "####Attempted to cancel entry but trade was triggered already"
		#Order is rejected
        elif order.status == OrderClass.Status_Rejected:
            print "ORDER REJECTED" + " ID: " + str(self.trade_id) 
            self.order_list.remove(order)
            if order.notes.startswith("LongStop") or order.notes.startswith("ShortStop"):
                self.sent_stop_order = False
            if order.notes.startswith("ShortEntry"):
                print "Is the stock CB? " + str(order.symbol)
		#Order is partially filled
        elif order.status == OrderClass.Status_Partial:
            print "Partial Fill - " + order.symbol + " - " + order.notes + " -shares executed: " + str(order.executed_size)
    
    def has_moved_stop_multiple_from_entry(self, bar):
        '''(bar) -> bool
        
        Take the latest bar from the new_bar function and depending on side
        will see if has moved some X multiple of the original stop from my entry.
        Will see the self.can_trail_now to True and will return True if it has.
        This is used for waiting until my trade is X in the money before trailing
        my stops.
        '''
        if self.side == "long":
            stop_size = self.long_entry - self.long_protective_stop
            print "STOP SIZE: " + str(stop_size)
            distance_itm = stop_size * self.stop_multiple_ITM_before_trail
            print "Distance ITM needed: " + str(distance_itm)
            print "Bar high: " + str(bar['high'])
            if (bar['high'] - self.long_entry) > distance_itm:
                #moved enough in last bar
                self.can_trail_now = True
                return True
            else:
                return False
        
        if self.side == "short":
            stop_size = self.short_protective_stop - self.short_entry
            print "STOP SIZE: " + str(stop_size)
            distance_itm = stop_size * self.stop_multiple_ITM_before_trail
            print "Distance ITM needed: " + str(distance_itm)
            print "Bar Low: " + str(bar['low'])
            if (self.short_entry - bar['low']) > distance_itm:
                #move enough in last bar
                self.can_trail_now = True
                return True
            else:
                return False
    
    def new_bar(self, bar_list):
		'''(list of price bars) -  None
		
		This is called from main script every time a new price bar is closed.
		'''
        self.cancel_pending_entry_orders()
        if not self.entry_triggered:
            print "Trade not triggered, closing"
            self.closed = True
        #Begin trail if have enough data
        if self.trail_exit_bars > 0:
            self.trade_open_for_bars += 1
            if self.trade_open_for_bars >= self.trail_exit_bars:
                if self.can_trail_now or self.has_moved_stop_multiple_from_entry(bar_list[-1]):
                    #Enough bars have closed to now update the trailing stop
                    print "Updating trailing stop-TRADE OPEN FOR %d BARS" % self.trade_open_for_bars
                    self.update_trailing_stop(bar_list)
                else:
                    print "Can't trail yet, hasn't moved enough"