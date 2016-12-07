# trade_class
An example of how to manage individual trades in Python.


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
