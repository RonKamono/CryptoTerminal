import webbrowser

def bybit_open(name):
    return webbrowser.open(url=f'https://www.bybit.com/trade/usdt/{name}'),

def binance_open(name):
    return webbrowser.open(url=f'https://www.binance.com/en/futures/{name}'),

def binx_open(name):
    name = name.replace("USDT", "-USDT")
    return webbrowser.open(url=f'https://bingx.com/en/perpetual/{name}')

def mexc_open(name):
    name = name.replace('USDT', "_USDT?type=linear_swap")
    return webbrowser.open(url=f'https://www.mexc.com/ru-RU/futures/{name}')