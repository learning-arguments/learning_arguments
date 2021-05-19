import os
import pandas as pd
import numpy as np
from logic import Case, Fact, CaseModel
from typing import *
from helpers import histogram

cwd = os.getcwd()


def load_csv_data(data_set_name: str) -> pd.DataFrame:
    return pd.read_csv(os.path.join(cwd, *["data", data_set_name]))


def bin_labels(n: int) -> List[str]:
    if n == 2:
        return ["low", "high"]
    elif n == 3:
        return ["low", "medium", "high"]
    elif n == 4:
        return ["very_low", "low", "high", "very_high"]
    elif n == 5:
        return ["very_low", "low", "medium", "high", "very_high"]
    else:
        return ["quantile_" + str(i) for i in range(1, n + 1)]


def bin_data_set(
    data_set: pd.DataFrame, n_bins: int, method="equal_depth"
) -> pd.DataFrame:
    binned_data = pd.DataFrame()
    for col in data_set.columns:
        column_labels = [label + "_" + col for label in bin_labels(n_bins)]
        if method == "equal_width":
            bin_edges = np.linspace(
                np.min(data_set[col]) - 1e-5,
                np.max(data_set[col]) + 1e-5,
                n_bins + 1,
            )
            binned_data[col + "_facts"] = pd.cut(
                data_set[col], bins=bin_edges, labels=column_labels
            )
        elif method == "equal_depth":
            binned_data[col + "_facts"] = pd.qcut(
                data_set[col].rank(method="first"),
                q=[0.0, 0.50, 1.0],
                labels=column_labels,
            )
    return binned_data


def to_fact(s: str, is_binary: bool) -> Fact:
    if is_binary:
        if s[:4] == "low_":
            return Fact("high_" + s[4:], False)
        else:
            return Fact(s, True)
    else:
        return Fact(s, True)


def generate_case_model(binned_data: pd.DataFrame, is_binary: bool) -> CaseModel:
    cases: Dict[Tuple[Any, ...], float] = dict()
    data_points = [tuple(binned_data.loc[i]) for i in binned_data.index]

    return CaseModel(
        [
            Case(
                probability=count / len(binned_data),
                facts=[to_fact(fact, is_binary) for fact in facts],
            )
            for facts, count in histogram(data_points).items()
        ]
    )
