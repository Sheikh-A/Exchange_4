from flask import Flask, request, g
from flask_restful import Resource, Api
from sqlalchemy import create_engine
from flask import jsonify
import json
import eth_account
import algosdk
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import load_only
from datetime import datetime
import sys

from models import Base, Order, Log
engine = create_engine('sqlite:///orders.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)

app = Flask(__name__)

@app.before_request
def create_session():
    g.session = scoped_session(DBSession)

@app.teardown_appcontext
def shutdown_session(response_or_exc):
    sys.stdout.flush()
    g.session.commit()
    g.session.remove()


""" Suggested helper methods """

def check_sig(payload,sig):
    pass

def fill_order(order,txes=[]):
    object_order = Order( sender_pk=order['sender_pk'],receiver_pk=order['receiver_pk'], buy_currency=order['buy_currency'], sell_currency=order['sell_currency'], buy_amount=order['buy_amount'], sell_amount=order['sell_amount'] )
    
    if 'creator_id' in order.keys():
        object_order.creator_id = order['creator_id']
    order = object_order
    #ADD
    session.add(order)
    #COMMIT
    session.commit()

    full_order_list = session.query(Order).filter(Order.filled == None).filter(Order.buy_currency == order.sell_currency).filter(Order.sell_currency == order.buy_currency).all()
    #Set Rate
    rate = 0
    #SET ID
    id = -1
    
    for order_num in full_order_list:
        new_rate = order_num.sell_amount / order_num.buy_amount
        if new_rate > rate:
            rate = new_rate
            id = order_num.id

    if rate >= order.buy_amount / order.sell_amount and id != -1:
        other = session.query(Order).get(id)
        order = session.query(Order).get(order.id)
        
        filled = datetime.now()
        
        other.filled = filled
        order.filled = filled
        
        
        order.counterparty_id = id
        other.counterparty_id = order.id
        
        session.commit()
        
        order_dictionary = {}
        
        if order.buy_amount > other.sell_amount:
            order_dictionary['creator_id'] = order.id

            order_dictionary['buy_currency'] = order.buy_currency
            order_dictionary['sell_currency'] = order.sell_currency
            
            order_dictionary['sender_pk'] = order.sender_pk
            order_dictionary['receiver_pk'] = order.receiver_pk
            
            order_dictionary['buy_amount'] = order.buy_amount - other.sell_amount
            order_dictionary['sell_amount'] = order.sell_amount - other.buy_amount
            process_order(order_dictionary)

        elif other.buy_amount > order.sell_amount:
            order_dictionary['creator_id'] = other.id

            
            order_dictionary['buy_currency'] = other.buy_currency
            order_dictionary['sell_currency'] = other.sell_currency

            order_dictionary['sender_pk'] = other.sender_pk
            order_dictionary['receiver_pk'] = other.receiver_pk

            order_dictionary['buy_amount'] = other.buy_amount - order.sell_amount
            order_dictionary['sell_amount'] = other.sell_amount - order.buy_amount
            
            process_order(order_dictionary)

def log_message(d):
    log_object = Log( message=d)
    g.session.add(log_object)
    g.session.commit()

""" End of helper methods """



@app.route('/trade', methods=['POST'])
def trade():
    print("In trade endpoint")
    if request.method == "POST":
        content = request.get_json(silent=True)
        print( f"content = {json.dumps(content)}" )
        d_columns = [ "sender_pk", "receiver_pk", "buy_currency", "sell_currency", "buy_amount", "sell_amount", "platform" ]
        data_fields = [ "sig", "payload" ]

        for datafield in data_fields:
            if not datafield in content.keys():

                
                print( json.dumps(content) )
                
                log_message(content)
                return jsonify( False )

        for data in d_columns:
            if not data in content['payload'].keys():
                print( json.dumps(content) )
                log_message(content)
                return jsonify( False )

        #Your code here
        #Note that you can access the database session using g.session
        sig = content["sig"]
        pk = content["payload"]["sender_pk"]
        msg = json.dumps(content["payload"])
        platform = content["payload"]["platform"]
        result = True
        if platform == 'Ethereum':
            eth_encoded_msg = eth_account.messages.encode_defunct(text=msg)
            if eth_account.Account.recover_message(eth_encoded_msg,signature=sig) == pk:
                result = True
            else:
                result = False
        else:
            if algosdk.util.verify_bytes(msg.encode('utf-8'),sig,pk):
                result = True
            else:
                result = False
        if result == True:
            order = {}
            order['sender_pk'] = content["payload"]["sender_pk"]
            order['receiver_pk'] = content["payload"]["receiver_pk"]
            order['buy_currency'] = content["payload"]["buy_currency"]
            order['sell_currency'] = content["payload"]["sell_currency"]
            order['buy_amount'] = content["payload"]["buy_amount"]
            order['sell_amount'] = content["payload"]["sell_amount"]
            order_obj = Order( sender_pk=order['sender_pk'],receiver_pk=order['receiver_pk'], buy_currency=order['buy_currency'], sell_currency=order['sell_currency'], buy_amount=order['buy_amount'], sell_amount=order['sell_amount'] )
            g.session.add(order_obj)
            g.session.commit()
        else:
            log_message(msg)

        # TODO: Fill the order
        fill_order(content["payload"])
        # TODO: Be sure to return jsonify(True) or jsonify(False) depending on if the method was successful
        return jsonify(result)


@app.route('/order_book')
def order_book():
    #Your code here
    orders = g.session.query(Order)
    result = {}
    list = []
    for order in orders:
        cur = {}
        cur['sender_pk'] = order.sender_pk
        cur['receiver_pk'] = order.receiver_pk
        cur['buy_currency'] = order.buy_currency
        cur['sell_currency'] = order.sell_currency
        cur['buy_amount'] = order.buy_amount
        cur['sell_amount'] = order.sell_amount
        cur['signature'] = order.signature
        list.append(cur)
    result['data'] = list
    #Note that you can access the database session using g.session
    return jsonify(result)

if __name__ == '__main__':
    app.run(port='5002')
