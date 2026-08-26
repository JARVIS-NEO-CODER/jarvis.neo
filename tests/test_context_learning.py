from core.context_learning import learn_signal, learned_signals


class FakeMemory:
    def __init__(self):
        self.facts = []

    def remember_fact(self, *args, **kwargs):
        self.facts.append((args, kwargs))
        return len(self.facts)

    def get_facts(self, **kwargs):
        return [
            {"value": {"context": "GAMING", "signal": "steam.exe"}, "confidence": 0.9}
        ]


def test_learn_signal_persists_neutral_association():
    memory = FakeMemory()
    assert learn_signal(memory, "gaming", "Steam.exe", 0.8) == 1
    assert memory.facts[0][1]["source"] == "context_learning"


def test_learned_signals_filters_context():
    memory = FakeMemory()
    assert learned_signals(memory, "gaming")
    assert learned_signals(memory, "coding") == []
