"""
VeriTrace Forge Module - Synthetic Identity & Sleeper Agent Generator
"""
from forge.generator import generate_timeline, generate_batch, generate_timeline_adversarial
from forge.mutation import mutate_params, params_to_generator_kwargs, describe_mutation, DEFAULT_PARAMS

__all__ = [
    "generate_timeline",
    "generate_batch",
    "generate_timeline_adversarial",
    "mutate_params",
    "params_to_generator_kwargs",
    "describe_mutation",
    "DEFAULT_PARAMS",
]
