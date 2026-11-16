from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_EVEN

cent = Decimal("0.01")
raw = [Decimal("0.335"), Decimal("0.335"), Decimal("0.335")]
print("line-rounded", sum(x.quantize(cent, rounding=ROUND_HALF_UP) for x in raw))
print("invoice-rounded", sum(raw).quantize(cent, rounding=ROUND_HALF_UP))
print("float-constructor", Decimal(1.005).quantize(cent, rounding=ROUND_HALF_UP))
print("text-constructor", Decimal("1.005").quantize(cent, rounding=ROUND_HALF_UP))
print("half-up", Decimal("0.325").quantize(cent, rounding=ROUND_HALF_UP))
print("half-even", Decimal("0.325").quantize(cent, rounding=ROUND_HALF_EVEN))
print("binary-round", round(2.675, 2))
