# -*- coding: utf-8 -*-
"""food_vision.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1Zo49r8OJBmGMqjdkoj40wDwDgEbt-xMM

# Food Vision Big!!!
"""

!pip install tensorflow
import tensorflow as tf
print(tf.__version__)

!nvidia-smi -L

# !pip install tensorflow_datasets

!wget https://raw.githubusercontent.com/mrdbourke/tensorflow-deep-learning/main/extras/helper_functions.py

import tensorflow as tf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras import mixed_precision
import tensorflow_datasets as tfds
from sklearn.metrics import classification_report, confusion_matrix
from helper_functions import create_tensorboard_callback, plot_loss_curves, compare_historys, make_confusion_matrix

tfds_datasets = tfds.list_builders()
print('food101' in tfds_datasets)

(train_data, test_data), ds_info = tfds.load(name='food101', 
                                             split=['train', 'validation'],
                                             shuffle_files=True,
                                             as_supervised=True,                # tuple (data, label)
                                             with_info=True)

ds_info.features

"""* class_names
* shape
* one hot encode or label encoded
* data type
* labels match with class_names
"""

class_names = ds_info.features['label'].names
class_names[:10]

train_sample = train_data.take(1)
train_sample

for image, label in train_sample:
  print(f"""
    Image shape: {image.shape}
    Image data type: {image.dtype}
    Target class from food101 (tensor form): {label}
    Class name (str): {class_names[label.numpy()]}
  """)

image

tf.reduce_min(image), tf.reduce_max(image)

"""# plot an image"""

def show_image(image, label, figsize=(10, 7)):
  plt.figure(figsize=figsize)
  plt.imshow(image)
  plt.title(f'Sample image from Food101 dataset, {class_names[label.numpy()]}')
  plt.axis(False)

show_image(image, label)

"""# create preprocessing functions for the data
* batched, normalized, ...
* our data: uint, not scaled (0, 255), different image size
"""

def preprocess_image(image, label, img_shape=224, scale=False):
  """
  convert type from uint8 to float32
  reshape to [img_shape, img_shape, color_channels]
  """
  # resize
  image = tf.image.resize(image, size=[img_shape, img_shape])
  
  # scale
  image = image/255. if scale else image
  
  # convert and return
  return tf.cast(image, tf.float32), label

preprocessed_img = preprocess_image(image, label, scale=False)[0]
print(f'Image before preprocessing:\n {image[:2]}..., \nShape: {image.shape}, DataType: {image.dtype}')
print(f'Image after preprocessing:\n {preprocessed_img[:2]}..., \nShape: {preprocessed_img.shape}, DataType: {preprocessed_img.dtype}')

show_image(image, label)
show_image(preprocessed_img/255., label)

train_data = train_data.map(map_func=preprocess_image, num_parallel_calls=tf.data.AUTOTUNE)
train_data = train_data.shuffle(buffer_size=1000).batch(32).prefetch(buffer_size=tf.data.AUTOTUNE)

test_data = test_data.map(map_func=preprocess_image, num_parallel_calls=tf.data.AUTOTUNE).batch(32).prefetch(tf.data.AUTOTUNE)

train_data, test_data

"""# create callbacks"""

tensorboard_callback = create_tensorboard_callback(dir_name='food_vision',
                                                   experiment_name='food_vision_feature_extraction')

checkpoint_path = 'food_vision_model_checkpoints/checkpoint.ckpt'
model_checkpoint = tf.keras.callbacks.ModelCheckpoint(checkpoint_path, 
                                                      monitor='val_accuracy',
                                                      save_weights_only=True,
                                                      save_best_only=True,
                                                      verbose=0)

lr_reducer = tf.keras.callbacks.ReduceLROnPlateau(monitor='val_loss',
                                                  factor=.2,
                                                  patience=2,
                                                  verbose=0)

mixed_precision.set_global_policy('mixed_float16')
mixed_precision.global_policy()

data_augmentation = tf.keras.models.Sequential([
    layers.RandomFlip('horizontal'),
    layers.RandomRotation(.2),
    layers.RandomZoom(.2),
    layers.RandomHeight(.2),
    layers.RandomWidth(.2),
    # layers.Rescaling(1./255)
], name="data_augmentation")

base_model = tf.keras.applications.EfficientNetB0(include_top=False)
base_model.trainable = False

input_shape = (224, 224, 3)
inputs = layers.Input(shape=input_shape, name='input_layer')
x = data_augmentation(inputs)
x = base_model(x, training=False)
x = layers.GlobalAveragePooling2D(name='global_average_pooling_2d')(x)
x = layers.Dense(len(train_data), name='dense')(x)
outputs = layers.Activation('softmax', dtype=tf.float32, name='softmax_layer')(x)
efficientnetb0_model = tf.keras.Model(inputs, outputs)

efficientnetb0_model.compile(loss=tf.keras.losses.SparseCategoricalCrossentropy(),
                             optimizer=tf.keras.optimizers.Adam(),
                             metrics=['accuracy'])

efficientnetb0_model.summary()

for layer in efficientnetb0_model.layers:
  print(layer.name, layer.trainable, layer.dtype, layer.dtype_policy)

for layer in base_model.layers:
  print(layer.name, layer.trainable, layer.dtype, layer.dtype_policy)

initial_epochs = 3
history_efficientnetb0_feat = efficientnetb0_model.fit(train_data,
                                                       epochs=initial_epochs,
                                                       steps_per_epoch=len(train_data),
                                                       validation_data=test_data,
                                                       validation_steps=(.15 * len(test_data)),
                                                       callbacks=[tensorboard_callback, 
                                                                  model_checkpoint])

results_efficientnetb0_feat = efficientnetb0_model.evaluate(test_data)
results_efficientnetb0_feat

"""# save the model"""

# efficientnetb0_model.save('models/efficientnetb0_model_feat.h5')

from google.colab import files
# files.download('model_efficientnetb0_feat.h5')

from google.colab import drive
drive.mount('/content/drive')
# efficientnetb0_model.save('content/drive/MyDrive/food_vision/models/efficientnetb0_model_feat.h5')

# loaded_model = tf.keras.models.load_model('models/efficientnetb0_feat.h5')

# np.isclose(results_efficientnetb0_feat, results_loaded_efficientnetb0)

# loaded_model = tf.keras.models.load_model('content/drive/MyDrive/food_vision/models/efficientnetb0_model_feat')

# np.isclose(results_efficientnetb0_feat, results_loaded_efficientnetb0)

"""## load the pretrained model and evaluate it"""

!wget https://storage.googleapis.com/ztm_tf_course/food_vision/07_efficientnetb0_feature_extract_model_mixed_precision.zip
!mkdir models
!unzip 07_efficientnetb0_feature_extract_model_mixed_precision.zip -d models
loaded_model = tf.keras.models.load_model('models/07_efficientnetb0_feature_extract_model_mixed_precision')

results_loaded_efficientnetb0 = loaded_model.evaluate(test_data)
results_loaded_efficientnetb0

loaded_model.summary()

"""# fine tune and beat the DeepFood paper 77.4% top-1 accuracy"""

loaded_model.trainable = True

for layer in loaded_model.layers[1].layers:
  print(layer.name, layer.trainable, layer.dtype, layer.dtype_policy)

early_stopping_callback = tf.keras.callbacks.EarlyStopping(monitor='val_loss',
                                                  patience=3,
                                                  mode='min',
                                                  verbose=1)

checkpoint_path = 'models/checkpoint_fine_tuning.ckpt'
model_checkpoint_callback = tf.keras.callbacks.ModelCheckpoint(checkpoint_path,
                                                      monitor='val_loss',
                                                      save_weights_only=True,
                                                      save_best_only=True,
                                                      verbose=1)

tensorboard_callback = create_tensorboard_callback(dir_name='food_vision',
                                                  experiment_name='food_vision_big_fine')

loaded_model.compile(loss=tf.keras.losses.SparseCategoricalCrossentropy(),
                     optimizer=tf.keras.optimizers.Adam(0.0001),
                     metrics=['accuracy'])

train_data, test_data

fine_tune_epochs = initial_epochs + 100
history_mixed_pre_fine = loaded_model.fit(train_data,
                                          epochs=fine_tune_epochs,
                                          steps_per_epoch=len(train_data),
                                          validation_data=test_data,
                                          validation_steps=(.15 * len(test_data)),
                                          initial_epoch=history_efficientnetb0_feat.epoch[-1],
                                          callbacks=[tensorboard_callback,
                                                     model_checkpoint,
                                                     early_stopping_callback])

results_efficientnetb0_fine_10 = loaded_model.evaluate(test_data)
results_efficientnetb0_fine_10

plot_loss_curves(history_mixed_pre_fine)

# loaded_model.save('models/food_vision_big_efficientnetb0_model_mixed_pre_fine.h5')
# loaded_model.save('content/drive/MyDrive/food_vision/models/food_vision_big_efficientnetb0_model_mixed_pre_fine.h5')

# loaded_model.save_weights('models/food_vision_big_efficientnetb0_model_mixed_pre_fine_weights.h5')

from google.colab import files
# files.download('models/food_vision_big_efficientnetb0_model_mixed_pre_fine_weights.h5')

# loaded_model = loaded_model.load_weights('models/food_vision_big_efficientnetb0_model_mixed_pre_fine_weights.h5')

"""# upload and view on tensorboard dev"""

!tensorboard dev upload --logdir ./food_vision \
  --name "food_vision_big_mixedpre_fine_efficientnetb0" \
  --description "food vision big!!! app with EfficientNetB0 model fine tuned using mixed_precision and pipeline" \
  --one_shot

"""

```
`# This is formatted as code`
```

* Done. View your TensorBoard at https://tensorboard.dev/experiment/GFbokWgORGmIrYTmCZ6Z1Q/"""

!tensorboard dev list

# !tensorboard dev delete --experiment_id

"""# Evaluate"""

!wget https://storage.googleapis.com/ztm_tf_course/food_vision/07_efficientnetb0_fine_tuned_101_classes_mixed_precision.zip
!unzip "07_efficientnetb0_fine_tuned_101_classes_mixed_precision.zip"

# doesnt have metadata so we must use hub.KerasLayer
# loaded_model = tf.saved_model.load("07_efficientnetb0_fine_tuned_101_classes_mixed_precision/")

# doesn't have metadata
# tf.keras.models.save_model(loaded_model, 'models/loaded_model_fine.h5')

import tensorflow_hub as hub
loaded_model = tf.keras.Sequential([
    hub.KerasLayer('/content/07_efficientnetb0_fine_tuned_101_classes_mixed_precision', trainable=True)
    ])

loaded_model.compile(loss='sparse_categorical_crossentropy',
                     optimizer=tf.keras.optimizers.Adam(.0001),
                     metrics=['accuracy'])

pred_probs = efficientnetb0_model.predict(test_data)
y_preds = tf.argmax(pred_probs, axis=1)
y_labels = []
for image, label in test_data.unbatch():
  y_labels.append(label)

true_classes = [class_names[i] for i in y_labels]
pred_classes = [class_names[i] for i in y_preds]

pred_probs[:2], y_preds[:2], y_labels[:2], true_classes[:2], pred_classes[:2],

classification_report_dict = classification_report(y_labels, y_preds, output_dict=True)
classification_report_dict

class_f1_score, class_recall, class_precision = {}, {}, {}
for k, v in classification_report_dict.items():
  if k == 'accuracy':
    break
  class_f1_score[class_names[int(k)]] = v['f1-score']
  class_recall[class_names[int(k)]] = v['recall']
  class_precision[class_names[int(k)]] = v['precision']

f1_score_df = pd.DataFrame({
    'class_name':list(class_f1_score.keys()),
    'f1_score':list(class_f1_score.values())
}).sort_values('f1_score', ascending=False)
f1_score_df.head()

def plot_f1_score(f1_score_df):
  fig, ax = plt.subplots(figsize=(12, 25))
  scores = ax.barh(range(len(f1_score_df)), f1_score_df['f1_score'].values)
  ax.set_yticks(range(len(f1_score_df)))
  ax.set_yticklabels(f1_score_df['class_name'])
  ax.set_xlabel('f1_score')
  ax.set_title('F1_score for 101 classes')
  ax.invert_yaxis()
  autolabel(scores, axis=ax)

def autolabel(rects, axis):
  for rect in rects:
    axis.text(1.03 * rect.get_width(), rect.get_y() + rect.get_height() / 1.5,
              f"{rect.get_width():.2f}",
              ha='center', va='bottom')

plot_f1_score(f1_score_df)

"""## confusion matrix"""

import itertools
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import confusion_matrix

# Our function needs a different name to sklearn's plot_confusion_matrix
def make_confusion_matrix(y_true, y_pred, classes=None, figsize=(10, 10), text_size=15, norm=False, savefig=False): 
  """Makes a labelled confusion matrix comparing predictions and ground truth labels.

  If classes is passed, confusion matrix will be labelled, if not, integer class values
  will be used.

  Args:
    y_true: Array of truth labels (must be same shape as y_pred).
    y_pred: Array of predicted labels (must be same shape as y_true).
    classes: Array of class labels (e.g. string form). If `None`, integer labels are used.
    figsize: Size of output figure (default=(10, 10)).
    text_size: Size of output figure text (default=15).
    norm: normalize values or not (default=False).
    savefig: save confusion matrix to file (default=False).
  
  Returns:
    A labelled confusion matrix plot comparing y_true and y_pred.

  Example usage:
    make_confusion_matrix(y_true=test_labels, # ground truth test labels
                          y_pred=y_preds, # predicted labels
                          classes=class_names, # array of class label names
                          figsize=(15, 15),
                          text_size=10)
  """  
  # Create the confustion matrix
  cm = confusion_matrix(y_true, y_pred)
  cm_norm = cm.astype("float") / cm.sum(axis=1)[:, np.newaxis] # normalize it
  n_classes = cm.shape[0] # find the number of classes we're dealing with

  # Plot the figure and make it pretty
  fig, ax = plt.subplots(figsize=figsize)
  cax = ax.matshow(cm, cmap=plt.cm.Blues) # colors will represent how 'correct' a class is, darker == better
  fig.colorbar(cax)

  # Are there a list of classes?
  if classes:
    labels = classes
  else:
    labels = np.arange(cm.shape[0])
  
  # Label the axes
  ax.set(title="Confusion Matrix",
         xlabel="Predicted label",
         ylabel="True label",
         xticks=np.arange(n_classes), # create enough axis slots for each class
         yticks=np.arange(n_classes), 
         xticklabels=labels, # axes will labeled with class names (if they exist) or ints
         yticklabels=labels)
  
  # Make x-axis labels appear on bottom
  ax.xaxis.set_label_position("bottom")
  ax.xaxis.tick_bottom()

  # x labels rotation
  plt.xticks(rotation=70, fontsize=text_size)
  plt.yticks(fontsize=text_size)

  # Set the threshold for different colors
  threshold = (cm.max() + cm.min()) / 2.

  # Plot the text on each cell
  for i, j in itertools.product(range(cm.shape[0]), range(cm.shape[1])):
    if norm:
      plt.text(j, i, f"{cm[i, j]} ({cm_norm[i, j]*100:.1f}%)",
              horizontalalignment="center",
              color="white" if cm[i, j] > threshold else "black",
              size=text_size)
    else:
      plt.text(j, i, f"{cm[i, j]}",
              horizontalalignment="center",
              color="white" if cm[i, j] > threshold else "black",
              size=text_size)

  # Save the figure to the current working directory
  if savefig:
    fig.savefig("confusion_matrix.png")

make_confusion_matrix(y_labels, y_preds, classes=class_names, figsize=(100, 100), text_size=20)

for i, (image, label) in enumerate(test_data.unbatch().take(9)):
  print(i, image.shape, label.shape, tf.expand_dims(image, axis=0).shape)

## random plots
import random 

def visualize_random_class(model, class_names=class_names, figsize=(10, 10)):
  samples = test_data.unbatch().take(9)
  plt.figure(figsize=(10, 10))
  for i, (image, label) in enumerate(samples):
    y_probs = model.predict(tf.expand_dims(image, axis=0))
    y_pred = tf.argmax(y_probs, axis=1)
    pred_class = class_names[int(y_pred)]
    true_class = class_names[int(label)]

    # plot
    plt.subplot(3, 3, i + 1)
    plt.imshow(image/255.)
    title_color = 'green' if label == y_pred else 'red' 
    plt.title(f'actual: {true_class}, \npred: {pred_class}, prob: {y_probs.max():.2f}', c=title_color)
    plt.axis(False)

visualize_random_class(efficientnetb0_model, class_names=class_names, figsize=(20, 15))

"""## most wrong predictions"""

pred_df = pd.DataFrame({
    'y_labels':y_labels,
    'y_pred':y_preds,
    "pred_conf":pred_probs.max(axis=1),
    'true_classes':true_classes,
    'pred_classes':pred_classes
})
pred_df['pred_correct'] = pred_df["y_labels"] == pred_df['y_pred']
pred_df.head(10)

top_100_wrong = pred_df[pred_df['pred_correct'] == False].sort_values('pred_conf', ascending=False)[:100]
top_100_wrong.head()

top_100_wrong.iloc[0], top_100_wrong.index[0]

for j, idx in enumerate(top_100_wrong.index):
  print(j, idx, '\t')

# save images to plot
images = []
for i, (image, _) in enumerate(test_data.unbatch()):
  for idx in top_100_wrong.index:
    if i == idx:
      images.append((idx, image))

top_100_images = []
for idx in top_100_wrong.index:
  for j in images[:, 0]:
    if idx == j:
      top_100_images.append(images[idx, 1])

top_100_wrong['image'] = top_100_images
top_100_wrong.head()

top_100_wrong.index, test_data.unbatch(), test_data

import random

def visualize_wrong_predictions(top_100_wrong, figsize=(10, 10)):
  start_index = random.choice(range(0, 91))
  images_to_view = 9
  plt.figure(figsize=figsize)
  for i, row in enumerate(top_100_wrong[start_index: start_index + images_to_view].itertuples()):
    plt.subplot(3, 3, i + 1)
    _, _, _, pred_probs, y_label, y_pred, _, image = row
    plt.imshow(image/255.)
    title_color = 'green' if y_label == y_pred else 'red'
    plt.title(f'actual: {y_label}, pred: {y_pred}, \nprob: {pred_probs:.2f}', c=title_color)
    plt.axis(False)

visualize_wrong_predictions(top_100_wrong, figsize=(20, 20))

"""# custom data"""

!wget https://storage.googleapis.com/ztm_tf_course/food_vision/custom_food_images.zip

from helper_functions import unzip_data
!unzip_data('custom_food_images.zip')

import os
custom_images = ["custom_food_images/" + img_path for img_path in os.listdir("custom_food_images/")]
custom_images

from helper_functions import load_and_prep_image

def visualize_custom_images(model, custom_images, figsize=(10, 7)):
  plt.figure(figsize=figsize)
  for i in range(len(custom_images)):
    img = load_and_prep_image(custom_images[i], scale=False)

    pred_probs = model.predict(tf.expand_dims(img, axis=0))
    y_pred = tf.argmax(pred_probs, axis=1)
    class_name = class_names[int(y_pred)]

    plt.subplot(len(custom_images), 1, i + 1)  
    plt.imshow(img/255.)
    plt.title(f'pred: {class_name}, prob: {pred_probs.argmax():.2f}')
    plt.axis(False)

visualize_custom_images(efficientnetb0_model, custom_images)

"""# EfficientNetB4

* disconnect and delete runtime and begin training on EfficientNetB4_model
"""

import tensorflow as tf
from tensorflow import keras
import tensorflow_datasets as tfds
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from tensorflow.keras import layers, models, optimizers, losses, callbacks, mixed_precision

!wget https://raw.githubusercontent.com/mrdbourke/tensorflow-deep-learning/main/extras/helper_functions.py
from helper_functions import plot_loss_curves, create_tensorboard_callback, compare_historys

(train_data, test_data), ds_info = tfds.load(name='food101',
                                             split=['train', 'validation'],
                                             shuffle_files=True,
                                             as_supervised=True,
                                             with_info=True)

ds_info.features

class_names = ds_info.features['label'].names
class_names[:10]

"""## visualize images"""

for image, label in test_data.take(1):
  print(image.shape, image.dtype, label.shape, label.dtype)
show_image(image, label)

"""## prepare data"""

train_data = train_data.map(map_func=preprocess_image, num_parallel_calls=tf.data.AUTOTUNE) \
  .shuffle(buffer_size=1000).batch(32).prefetch(buffer_size=tf.data.AUTOTUNE)

test_data = test_data.map(map_func=preprocess_image, num_parallel_calls=tf.data.AUTOTUNE) \
  .batch(32).prefetch(buffer_size=tf.data.AUTOTUNE)

train_data, test_data

"""## model"""

# callbacks
tensorboard_callback = create_tensorboard_callback(dir_name='food_vision',
                                                   experiment_name='food_vision_big_EfficientNetB4_model_feat')

checkpoint_path = 'checkpoints/EfficientNetB4_feat_checkpoint.ckpt'
model_checkpoint = callbacks.ModelCheckpoint(checkpoint_path,
                                          monitor='val_loss',
                                          save_best_only=True,
                                          save_weights_only=True,
                                          mode='min',
                                          verbose=1)

lr_reducer = callbacks.ReduceLROnPlateau(monitor='val_loss',
                                         factor=.2,
                                         patience=2,
                                         min_lr=1e-7,
                                         mode='min',
                                         verbose=1)

data_augmentation = models.Sequential([
    layers.RandomFlip('horizontal'),
    layers.RandomRotation(.2),
    layers.RandomZoom(.2),
    layers.RandomHeight(.2),
    layers.RandomWidth(.2),
    # layers.Rescaling(1./255)
], name='data_augmentation')

mixed_precision.set_global_policy(policy='mixed_float16')

base_model = tf.keras.applications.EfficientNetB4(include_top=False)
base_model.trainable = False

input_shape = (224, 224, 3)
inputs = layers.Input(shape=input_shape, name='input_layer')
x = data_augmentation(inputs)
x = base_model(x, training=False)
x = layers.GlobalAveragePooling2D(name="global_average_pooling_2D")(x)
x = layers.Dense(len(train_data), name='output_layer')(x)
outputs = layers.Activation('softmax', dtype=tf.float32, name="softmax_layer")(x)

EfficientNetB4_model = keras.Model(inputs, outputs, name='EfficientNetB4_model')

EfficientNetB4_model.compile(loss=losses.SparseCategoricalCrossentropy(),
                             optimizer=optimizers.Adam(),
                             metrics=['accuracy'])

EfficientNetB4_model.summary()

tf.keras.utils.plot_model(EfficientNetB4_model)

initial_epochs = 3
history_efficientnetb4_feat = EfficientNetB4_model.fit(
    train_data,
    epochs=initial_epochs,
    steps_per_epoch=len(train_data),
    validation_data=test_data,
    validation_steps=(.15 * len(test_data)),
    callbacks=[tensorboard_callback, 
               model_checkpoint, 
               lr_reducer]
)

results_efficientnetb4_feat = EfficientNetB4_model.evaluate(test_data)
results_efficientnetb4_feat

plot_loss_curves(history_efficientnetb4_feat)

"""## fine tuning"""

base_model.trainable = True
for layer in base_model.layers[:-10]:
  layer.trainable = False
for layer in EfficientNetB4_model.layers:
  print(layer.name, layer.trainable, layer.dtype, layer.dtype_policy)

tensorboard_callback = create_tensorboard_callback(dir_name='food_vision',
                                                   experiment_name='food_vision_EfficientNetB4_fine_10')

early_stopping = callbacks.EarlyStopping(monitor='val_loss',
                                        patience=2,
                                        mode='min',
                                        verbose=1)

EfficientNetB4_model.compile(loss=losses.SparseCategoricalCrossentropy(),
                             optimizer=optimizers.Adam(0.0001),
                             metrics=['accuracy'])

fine_tune_epochs = initial_epochs + 100
history_efficientnetb4_fine_10 = EfficientNetB4_model.fit(
    train_data,
    epochs=fine_tune_epochs,
    steps_per_epoch=len(train_data),
    initial_epoch=history_efficientnetb4_feat.epoch[-1],
    validation_data=test_data,
    validation_steps=(.15 * len(test_data)),
    callbacks=[tensorboard_callback, 
               lr_reducer, 
               early_stopping]
)

results_efficientnetb4_fine_10 = EfficientNetB4_model.evaluate(test_data)
results_efficientnetb4_fine_10

plot_loss_curves(history_efficientnetb4_fine_10)

compare_historys(original_history=history_efficientnetb4_feat,
                 new_history=history_efficientnetb4_fine_10,
                 initial_epochs=initial_epochs)

"""## tensorboard visualization"""

!tensorboard dev upload --logdir ./food_vision \
  --name "food_vision_efficientnetb4_fine_10" \
  --description "food vision efficientnetb4 model on food101 dataset feature extraction for 3 epochs and fine tuning 10 layers with earlystopping" \
  --one_shot

"""* Done. View your TensorBoard at https://tensorboard.dev/experiment/A9dsG20XSAumYnnpYBOiEw/"""

!tensorboard dev list

# !tensorboard dev delete --experiment_id

# from google.colab import drive
# drive.mount('/content/drive/')

# EfficientNetB4_model.save('models/EfficientNetB4_model_feat_3_fine_10.h5')
# EfficientNetB4_model.save('/content/drive/MyDrive/food_vision/models/EfficientNetB4_feat_3_fine_10.h5')

# json serialization error in tf 2.11
# model = models.load_model('models/EfficientNetB4_model_feat_3_fine_10.h5')
# model = models.load_model('/content/drive/MyDrive/food_vision/models/EfficientNetB4_feat_3_fine_10.h5')

"""## Evaluation"""

pred_probs = EfficientNetB4_model.predict(test_data)
y_preds = tf.argmax(pred_probs, axis=1)
y_labels = []
img_index = 0
for image, label in test_data.unbatch():
  y_labels.append(label)
pred_classes = [class_names[i] for i in y_preds]
true_classes = [class_names[i] for i in y_labels]

from sklearn.metrics import classification_report
classification_report_dict = classification_report(y_labels, y_preds, output_dict=True)
classification_report_dict

class_names = ds_info.features['label'].names
class_names

class_f1_score = {}
for k, v in classification_report_dict.items():
  if k == 'accuracy':
    break
  class_f1_score[class_names[int(k)]] = v['f1-score']
class_f1_score

f1_score_dict = pd.DataFrame({
    'class_name':list(class_f1_score.keys()),
    'f1_score':list(class_f1_score.values())
}).sort_values('f1_score', ascending=False)
f1_score_dict.head()

plot_f1_score(f1_score_dict)

make_confusion_matrix(y_labels, y_preds, classes=class_names, figsize=(100, 100), text_size=20)

visualize_random_class(EfficientNetB4_model)

pred_df = pd.DataFrame({   
    'y_labels':y_labels,
    'y_preds':y_preds,
    'pred_conf':pred_probs.max(axis=1),
    'true_classes':true_classes,
    'pred_classes':pred_classes,
})
pred_df['pred_correct'] = pred_df['y_preds'] == pred_df['y_labels']
pred_df.head()

top_100_wrong = pred_df[pred_df['pred_correct'] == False].sort_values('pred_conf', ascending=False)[:100]
top_100_wrong.head()

# save images to plot
images = []
for i, (image, _) in enumerate(test_data.unbatch()):
  for idx in top_100_wrong.index:
    if i == idx:
      images.append((idx, image))

top_100_images = []
for idx in top_100_wrong.index:
  for j in images[:, 0]:
    if idx == j:
      top_100_images.append(images[idx, 1])

top_100_wrong['image'] = top_100_images
top_100_wrong.head()

visualize_wrong_predictions(top_100_wrong, figsize=(20, 20))

"""## custom_images"""

!wget https://storage.googleapis.com/ztm_tf_course/food_vision/custom_food_images.zip
!unzip "custom_food_images.zip"

import os
custom_images = ["custom_food_images/" + img_path for img_path in os.listdir("custom_food_images/")]
custom_images

visualize_custom_images(EfficientNetB4_model, custom_images, figsize=(20, 20))

# EfficientNetB4_model.save_weights('models/food_vision_EfficientNetB4_fine_10.h5')

# EfficientNetB4_model.load_weights('models/food_vision_EfficientNetB4_fine_10.h5')

