# ML Assisted Labeling Plugin  

This plugin lets you label your tabular, image or audio data efficiently by leveraging webapps and active learning recipes.

Not all samples bring the same amount of information when it comes to training a model. Labeling a very similar to an already labeled sample might not bring any improvement to the model performance. Active learning aims at estimating how much additional information labeling a sample can bring to a model and select the next sample to label accordingly. As an example, see how active learning performs compare to random sample annotation on a task of predicting wine color:
![](resource/img-doc/active-learning-perf.png)  

## Description  

This plugin offers a collection of visual webapps to label data (whether tabular, images or sound),
a visual recipe to determine which sample needs to be labeled next, as well as a scenario trigger.

- [Data labeling (webapp)](#labeling-webapp)
- [Score an unlabeled dataset (recipe)](#active-learning-recipe)
- [Active Learning setup (scenario)](#active-learning-scenario)

## When to use this plugin

The webapp purpose is to ease the labeling task. For large datasets or with a limited labeling budget, the Active Learning recipe and scenario can be leveraged. This becomes an iterative ML-assisted labeling process.

### Labeling Webapp
First, select the webapp that fits the data to be labeled.

![](resource/img-doc/webapp-selection.png)

All labeling webapps offer the same settings. For image labeling, those are:

![](resource/img-doc/webapp-settings.png)  

- `Images to label` - **managed folder** containing unlabeled images.

- `Categories` - set of **labels** to be assigned to images.

- `Labeling status and metadata` - **dataset** for the labeling metadata.

- `Labels dataset` - **dataset** to save labels into.

- `Label column name` - **column name** under which the manual labels will be stored.

- `Queries` (optional) - **dataset** containing the unlabeled data with an associated uncertainty score.

Note that the latter `queries` dataset is optional as labeling can always be done without Active Learning. In this case the user will be offered to label samples in a random order.

Once the settings are set, it's important to allow the webapp access to the corresponding datasets:
![](resource/img-doc/webapp-security.png)  

After the webapp has started, the annotation process can start.
![](resource/img-doc/webapp-ui.png)  

Note: For implementation purpose, in order to distinguish labeled from unlabeled samples in the tabular case, the webapp adds a column — called `label_id` by default — to the output dataset. This feature should not be used in any model.

### Active Learning Recipe  

When a sufficient number of samples has been labeled, a classifier from the DSS Visual Machine Learning interface can be trained to predict the labels, and be deployed in the project's flow.
In order to later use the Active Learning plugin, it's required to use a **python 3** environment to train the model. [Here's a walkthrough describing how to create a new code environment in DSS ](https://doc.dataiku.com/dss/latest/code-envs/operations-python.html#create-a-code-environment). Make sure that it's based on **python 3**.  

From the plugin, after the Query Sampler recipe is selected, the proposed inputs are:

 - `Classifier Model` - deployed classifier model.

 - `Unlabeled Data` - **dataset** containing the raw unlabeled data.

 - `Data to be labeled` - **dataset** containing the unlabeled data with an associated uncertainty score.

There is only one setting to choose from, the Active Learning strategy.
![](resource/img-doc/active-learning-recipe.png)

This plugin implements the three most common active learning strategies: Smallest confidence, Smallest margin,
and Greatest entropy. Here are their definitions in the general multiclass classification settings with *n* classes. `p^(i)` denotes the *i*-th highest predicted probability among all *n* classes.

Note: In the binary classification case, the ranking generated by all the different strategies will be the same. In that case, one should therefore go with the `Smallest confidence` strategy that is the less computationally costly.

#### Smallest confidence

This is a confidence score based on the probability of the most probable class.

<img src="https://render.githubusercontent.com/render/math?math=Confidence(X) = 1 - p^{(1)}">

#### Smallest margin

This approach focuses on the difference between the top two probabilities:

<img src="https://render.githubusercontent.com/render/math?math=Margin(X) = 1 - (p^{(1)} - p^{(2)})">

#### Greatest Entropy

Shannon's entropy measures the information carried by a random variable. This leads to the following definition:

<img src="https://render.githubusercontent.com/render/math?math=Entropy(X) = - \sum p^{(1)} \text{log}(p^{(1)})">

In order to have an homogeneous output, this is normalized between 0 and 1.

#### Sessions

Tracking performance evolution is useful in an active learning setting. For this purpose, a `session_id` counter on how many times the query sampler has been ran so far is added to the queries dataset.

This `session_id` is then reported in the metadata dataset, output of the labeling webapp.

### Active Learning Scenario

The Active Learning process is instrisically a loop in which the samples labeled so far and the trained classifier are leveraged to select the next batch of samples to be labeled. This loop takes place in DSS through the webapp, that takes the queries to fill the training data of the model, and a scenario that regularly trains the model and generates new queries.

To set up this scenario, this plugin proposes a custom trigger that can be used to retrain the model every `n` labelings. Here are the steps to follow to put in place the training:

- Create the scenario, add a custom trigger `Every n labeling`.

![](resource/img-doc/scenario-trigger.png)  

The following is then displayed:

![](resource/img-doc/scenario-trigger-option.png)  

Last but not least, the following three steps constitute the full Active Learning scenario:

![](resource/img-doc/scenario-steps.png)

# License

The ML Assisted labeling plugin is:

   Copyright (c) 2019 Dataiku SAS
   Licensed under the [MIT License](LICENSE.md).
