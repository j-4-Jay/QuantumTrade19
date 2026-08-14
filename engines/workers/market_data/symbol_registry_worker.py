
import json, os, threading
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional

REGISTRY_PATH = os.path.join("data", "symbol_registry.json")
DEFAULT_SEED_SYMBOLS = [
    {"symbol": "B-BTC_USDT", "tick_size": 0.1, "contract_size": 0.001, "maker_fee": 0.0005, "taker_fee": 0.001, "active": True, "asset_class": "crypto"},
    {"symbol": "B-ETH_USDT", "tick_size": 0.01, "contract_size": 0.01, "maker_fee": 0.0005, "taker_fee": 0.001, "active": True, "asset_class": "crypto"},
    {"symbol": "B-XAU_USDT", "tick_size": 0.01, "contract_size": 0.001, "maker_fee": 0.0005, "taker_fee": 0.001, "active": True, "asset_class": "metal"},
]

@dataclass
class SymbolInfo:
    symbol: str
    tick_size: float
    contract_size: float
    maker_fee: float
    taker_fee: float
    active: bool = True
    asset_class: str = "crypto"
    auto_live_traded_once: bool = False

class SymbolRegistryWorker:
    def __init__(self, path: str = REGISTRY_PATH) -> None:
        self._path = path
        self._lock = threading.RLock()
        self._symbols: Dict[str, SymbolInfo] = {}
        self._load_or_seed()

    def _load_or_seed(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        if os.path.exists(self._path):
            with open(self._path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            for row in raw:
                info = SymbolInfo(**row)
                self._symbols[info.symbol] = info
        else:
            for row in DEFAULT_SEED_SYMBOLS:
                info = SymbolInfo(**row)
                self._symbols[info.symbol] = info
            self._persist()

    def _persist(self) -> None:
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump([asdict(v) for v in self._symbols.values()], f, indent=2)

    def get_active_symbols(self) -> List[str]:
        with self._lock:
            return [s.symbol for s in self._symbols.values() if s.active]

    def get_all_symbols(self) -> List[str]:
        with self._lock:
            return list(self._symbols.keys())

    def get_symbol_info(self, symbol: str) -> Optional[SymbolInfo]:
        with self._lock:
            return self._symbols.get(symbol)

    def add_symbol(self, symbol, tick_size, contract_size, maker_fee, taker_fee, asset_class="crypto", active=True):
        with self._lock:
            info = SymbolInfo(symbol=symbol, tick_size=tick_size, contract_size=contract_size,
                               maker_fee=maker_fee, taker_fee=taker_fee, active=active, asset_class=asset_class)
            self._symbols[symbol] = info
            self._persist()
            return info

    def set_active(self, symbol, active):
        with self._lock:
            if symbol not in self._symbols:
                raise KeyError(f"Unknown symbol: {symbol}")
            self._symbols[symbol].active = active
            self._persist()

    def mark_auto_live_traded(self, symbol):
        with self._lock:
            if symbol in self._symbols:
                self._symbols[symbol].auto_live_traded_once = True
                self._persist()

    def get_deep_history_eligible(self):
        with self._lock:
            return [s.symbol for s in self._symbols.values() if s.auto_live_traded_once]

    def refresh_tick_table(self, updates):
        changed = []
        with self._lock:
            for symbol, new_tick in updates.items():
                info = self._symbols.get(symbol)
                if info and info.tick_size != new_tick:
                    info.tick_size = new_tick
                    changed.append(symbol)
            if changed:
                self._persist()
        return changed
