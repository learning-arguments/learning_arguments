# this file is a demo of what decision trees are capable of doing when it comes to rule-mining.
# to classify a new dataset, the file "decisionTreeClassifier" can be used

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

import time

import logic

myDataPath = "..\data\weatherAUS.csv"

df = pd.read_csv(myDataPath)

"""For now, we will simply drop the missing rows from the dataframe."""

df.dropna(inplace=True)

"""And now, convert the date into three seperate columns describing the year, month, and day."""

df['year'] = pd.DatetimeIndex(df['Date']).year
df['month'] = pd.DatetimeIndex(df['Date']).month
df['day'] = pd.DatetimeIndex(df['Date']).day

df.drop(columns=["Date"], inplace=True)

y = df["RainToday"]
df.drop(columns = ["RainToday", "RainTomorrow", "Rainfall"], inplace = True)

"""For decision trees, we need OneHotEncoding. This is why we need this piece of code here."""

df_new = pd.get_dummies(df ,columns=["Location", "WindGustDir", "WindDir9am", "WindDir3pm"],drop_first=False)
df_new

"""# Preparing the decision trees"""

X = df_new

from sklearn import tree

decTree = tree.DecisionTreeClassifier(random_state = 0)

decTree.fit(X, y)

decTree.get_params()

from sklearn.model_selection import cross_val_score

acc = cross_val_score(decTree, X, y, cv = 10, scoring = "f1_weighted")
acc = np.median(acc)

print('Performance of the vanilla decision tree model:', acc)

"""Ok! This is our vanilla performance!

## Hyperparameter Tuning: Bayesian Hyerparameter Tuning
"""

from skopt import BayesSearchCV
from skopt.space import Integer


search_spaces = {
    'max_depth': Integer(1, 50),
    'max_features': Integer(1, X.shape[1]),
    'min_samples_leaf': Integer(1, 1000),
    'min_samples_split': Integer(2, 1000)
}

clf = tree.DecisionTreeClassifier(random_state = 0)

opt = BayesSearchCV(
    estimator = clf, 
    search_spaces = search_spaces, scoring = 'f1_weighted',
    cv = 10,
    random_state=1, 
    n_jobs = -1, 
    refit = False)

print('Bayesian Optimization will require', opt.total_iterations, 'iterations.\n')

start_time = time.time()
opt.fit(X, y)

end_time = time.time()
print("Time used for Tuning the model:", (end_time - start_time)/60, "minutes.")

params = opt.best_params_

clf = tree.DecisionTreeClassifier(**params, random_state = 0)
acc = cross_val_score(clf, X, y, cv = 10, scoring = "f1_weighted")
acc = np.median(acc)
print('Performance of the optimized model:', acc)
print('Parameters used:', opt.best_params_, '\n')

from skopt.plots import plot_objective

_ = plot_objective(opt.optimizer_results_[0],
                   dimensions=["max_depth", "max_features", "min_samples_leaf", "min_samples_split"],
                   n_minimum_search=int(1e8))
plt.show()

import matplotlib.pyplot as plt

clf.fit(X, y)

plt.figure(figsize = (100, 100))
_= tree.plot_tree(clf, feature_names = X.columns, filled=True, fontsize = 10, proportion = True)
plt.show()

"""# Pruning the tree"""

path = clf.cost_complexity_pruning_path(X, y)
ccp_alphas, impurities = path.ccp_alphas, path.impurities

clfs = []
for ccp_alpha in ccp_alphas:
    clf = tree.DecisionTreeClassifier(**params, random_state=0, ccp_alpha=ccp_alpha)
    clf.fit(X, y)
    clfs.append(clf)
print("Number of nodes in the last tree is: {} with ccp_alpha: {}".format(
      clfs[-1].tree_.node_count, ccp_alphas[-1]))

accs = []
for clf in clfs:
    acc = cross_val_score(clf, X, y, cv = 10, scoring = "f1_weighted")
    acc = np.median(acc)
    accs.append(acc)

percentage = 1
entries = np.math.ceil(ccp_alphas.shape[0] * percentage)

fig, ax = plt.subplots()
ax.set_xlabel("alpha")
ax.set_ylabel("f1-score")
ax.plot(ccp_alphas[:entries], accs[:entries], marker='o', label="10-fold cv",
        drawstyle="steps-post")
ax.legend()
plt.grid()
plt.show()

print("Which alpha should be used to perform minimal cost-complexity pruning?")
myAlpha = input()
myAlpha = float(myAlpha)

'For the australian weather data, this was 0.01'
clfPruned = tree.DecisionTreeClassifier(**params, random_state = 0, ccp_alpha = myAlpha)
acc = cross_val_score(clfPruned, X, y, cv = 10, scoring = "f1_weighted")
acc = np.median(acc)
print('Performance of pruned tree:', acc, "\n")
print('Parameters of pruned tree:', opt.best_params_)

clfPruned.fit(X, y)

plt.figure(figsize = (10, 10))
_= tree.plot_tree(clfPruned, feature_names = X.columns, filled=True, fontsize = 10, proportion = True)
plt.show()

"""# Converting the tree into decision rules

The code down below is a modified version of the method found in the following article: https://mljar.com/blog/extract-rules-decision-tree/
"""

from sklearn.tree import _tree

def get_rules(tree, feature_names, class_names):
    tree_ = tree.tree_
    feature_name = [
        feature_names[i] if i != _tree.TREE_UNDEFINED else "undefined!"
        for i in tree_.feature
    ]

    paths = []
    path = []
    
    def recurse(node, path, paths):
        
        if tree_.feature[node] != _tree.TREE_UNDEFINED:
            name = feature_name[node]
            threshold = tree_.threshold[node]
            p1, p2 = list(path), list(path)
            p1 += [f"({name} <= {np.round(threshold, 3)})"]
            recurse(tree_.children_left[node], p1, paths)
            p2 += [f"({name} > {np.round(threshold, 3)})"]
            recurse(tree_.children_right[node], p2, paths)
        else:
            path += [(tree_.value[node], tree_.n_node_samples[node])]
            paths += [path]
            
    recurse(0, path, paths)

    # sort by samples count
    samples_count = [p[-1][1] for p in paths]
    ii = list(np.argsort(samples_count))
    paths = [paths[i] for i in reversed(ii)]
    
    rules = []
    for path in paths:
        rule = ""
        
        for p in path[:-1]:
            if rule != "":
                rule += ", "
            rule += str(p)
        rule += " -> "
        if class_names is None:
            rule += "response: "+str(np.round(path[-1][0][0][0],3))
        else:
            classes = path[-1][0][0]
            l = np.argmax(classes)
            rule += f"{class_names[l]}"
        rules += [rule]
        
    return rules

myClasses = ['NoRain', 'Rain']

print('\nThese rules were found by the final model:')
rules = get_rules(clfPruned, X.columns, myClasses)
for r in rules:
    print(r)

myArguments = list()
for r in rules:
    myArguments.append(logic.Argument.fromStr(r))