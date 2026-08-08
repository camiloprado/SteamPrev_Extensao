"""
Mocks centralizados para testes unitários da extensão.
Evita poluir o core/ com dados mockados.
"""

# Dados mockados da Steam para testes unitários
CON_DICT_MOCK_GAMES = {
    730: {
        "name": "Counter-Strike 2",
        "appid": 730,
        "is_free": True,
        "price": 0.0,
        "review_score": 83,
        "total_reviews": 7500000,
        "release_date": "2012-08-21",
        "header_image": "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/730/header.jpg",
    },
    1245620: {
        "name": "ELDEN RING",
        "appid": 1245620,
        "is_free": False,
        "price": 249.90,
        "review_score": 81,
        "total_reviews": 650000,
        "release_date": "2022-02-25",
        "header_image": "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/1245620/header.jpg",
    },
    413150: {
        "name": "Stardew Valley",
        "appid": 413150,
        "is_free": False,
        "price": 24.99,
        "review_score": 97,
        "total_reviews": 600000,
        "release_date": "2016-02-26",
        "header_image": "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/413150/header.jpg",
    },
    1091500: {
        "name": "Cyberpunk 2077",
        "appid": 1091500,
        "is_free": False,
        "price": 199.90,
        "review_score": 76,
        "total_reviews": 800000,
        "release_date": "2020-12-10",
        "header_image": "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/1091500/header.jpg",
    },
}

def _gerar_mock_padrao(arg_intAppid: int) -> dict:
    import random
    random.seed(arg_intAppid)
    return {
        "name": f"Jogo Steam #{arg_intAppid}",
        "appid": arg_intAppid,
        "is_free": False,
        "price": round(random.uniform(19.99, 299.90), 2),
        "review_score": random.randint(50, 95),
        "total_reviews": random.randint(100, 50000),
        "release_date": f"2020-01-01",
        "header_image": f"https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/{arg_intAppid}/header.jpg",
    }

async def get_mock_steam_game(arg_intAppid: int) -> dict | None:
    if arg_intAppid == 99999999:
        return None
    if arg_intAppid in CON_DICT_MOCK_GAMES:
        return CON_DICT_MOCK_GAMES[arg_intAppid].copy()
    return _gerar_mock_padrao(arg_intAppid)

def get_mock_itad_history(arg_floatPrecoBase: float, arg_intAnos: int = 5) -> list[dict]:
    if arg_floatPrecoBase <= 0:
        return []
    import random
    from datetime import datetime, timedelta
    random.seed(int(arg_floatPrecoBase))
    
    var_listHistorico = []
    var_dtAgora = datetime.now()
    var_dtInicio = var_dtAgora - timedelta(days=arg_intAnos * 365)
    
    var_dtCurrent = var_dtInicio
    while var_dtCurrent < var_dtAgora:
        var_intDiaDoAno = var_dtCurrent.timetuple().tm_yday
        var_boolSaleSeason = any(abs(var_intDiaDoAno - var_intSaleDay) < 15 for var_intSaleDay in [75, 177, 327, 355])
        
        if var_boolSaleSeason and random.random() < 0.6:
            var_intDesconto = random.choice([20, 30, 50, 75])
            var_floatPreco = round(arg_floatPrecoBase * (1 - var_intDesconto / 100), 2)
        elif random.random() < 0.1:
            var_intDesconto = random.choice([10, 20])
            var_floatPreco = round(arg_floatPrecoBase * (1 - var_intDesconto / 100), 2)
        else:
            var_floatPreco = arg_floatPrecoBase
            var_intDesconto = 0
            
        var_listHistorico.append({
            "timestamp": int(var_dtCurrent.timestamp()),
            "preco": var_floatPreco,
            "desconto": var_intDesconto
        })
        var_dtCurrent += timedelta(days=random.randint(15, 45))
        
    return var_listHistorico
