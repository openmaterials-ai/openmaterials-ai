"""The cure-kinetics domain: cure of a thermosetting resin.

Two method-neutral nodes in the Cure kinetics tier, CureConversion and
GlassTransitionTemperature. kamal_cure_conversion (method=kamal_sourour) reads
the existing Temperature node; dibenedetto_glass_transition
(method=dibenedetto_pascault_williams) maps the conversion to T_g. Hold time,
initial conversion, and fit constants ride in conditions.
"""
