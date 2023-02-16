# -*- coding: utf-8 -*-
"""convnetnoise.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1Kj4tYjEDCgdI9GnOXjqUx9Q41wMLzu8C
"""

from google.colab import drive
drive.mount('/gdrive')

# Commented out IPython magic to ensure Python compatibility.
# %cd "/gdrive/MyDrive/ChallengeANN"

# Update tensorflow in order to use ConvNext
!pip install tensorflow==2.10

import tensorflow as tf
import numpy as np
import os
import random
import pandas as pd
import seaborn as sns
import matplotlib as mpl
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.metrics import confusion_matrix
from PIL import Image
import shutil, random, json
from sklearn.utils import compute_class_weight
from datetime import datetime

tfk = tf.keras
tfkl = tf.keras.layers
print(tf.__version__)

# Random seed for reproducibility
seed = 42

random.seed(seed)
os.environ['PYTHONHASHSEED'] = str(seed)
np.random.seed(seed)
tf.random.set_seed(seed)
tf.compat.v1.set_random_seed(seed)
os.environ['TF_CUDNN_DETERMINISTIC'] = 'true'
os.environ['TF_DETERMINISTIC_OPS'] = 'true'

import warnings
import logging

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=Warning)
tf.get_logger().setLevel('INFO')
tf.autograph.set_verbosity(0)

tf.get_logger().setLevel(logging.ERROR)
tf.get_logger().setLevel('ERROR')
tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.ERROR)

import os.path
from os import path

dataset_dir = "training_data_final"

# Load the dataset to be used for classification
if not os.path.exists(dataset_dir):
    !unzip Training_dataset_homework1.zip

labels = ['Species1',
          'Species2',
          'Species3',
          'Species4',
          'Species5',
          'Species6',
          'Species7',
          'Species8']

from tensorflow.keras.preprocessing.image import ImageDataGenerator

batch_size = 16

# Create an instance of ImageDataGenerator with Data Augmentation
train_data_gen = ImageDataGenerator(rotation_range=360,
                                    height_shift_range=0.225,
                                    width_shift_range=0.225,
                                    zoom_range=0.425,
                                    brightness_range=(0.3, 1.5),
                                    channel_shift_range=50,
                                    shear_range=35,
                                    horizontal_flip=True,
                                    vertical_flip=True,
                                    fill_mode='reflect')

# Validation and testing set are not augmented in order to recognize real images
valid_data_gen = ImageDataGenerator()

test_data_gen = ImageDataGenerator()

# This is the last try we have done, in this case we wanted as many images as possible, to train the model as better as possible
trainingSplit = 0.95
validationSplit = 0.05

# Split dataset
# check if the tmp folder exist
random.seed(seed)
path = 'temp_split'
if os.path.exists(path):
    shutil.rmtree(path)
if not os.path.exists(path):
    os.mkdir(path)
if not os.path.exists(path + '/training'):
    os.mkdir(path + '/training')
if not os.path.exists(path + '/validation'):
    os.mkdir(path + '/validation')
if not os.path.exists(path + '/testing'):
    os.mkdir(path + '/testing')

# Source path
source = "training_data_final"

# Destination path
dest_train = path + '/training'
dest_valid = path + '/validation'
dest_test = path + '/testing'

# Create train and validation and test into the tmp folder
for folder in os.listdir(source):
    if not os.path.exists(dest_train + '/' + folder):
        os.mkdir(dest_train + '/' + folder)
    if not os.path.exists(dest_valid + '/' + folder):
        os.mkdir(dest_valid + '/' + folder)
    if not os.path.exists(dest_test + '/' + folder):
        os.mkdir(dest_test + '/' + folder)

    cl = source + '/' + folder  # Create path of the class
    files = os.listdir(cl)  # List of files for the class
    random.shuffle(files)
    # In the following part we randomically create duplicate of samples when we have done over-sampling
    # Create training set randomly
    for i in range(int(len(files) * trainingSplit)):
        dest = shutil.copy(cl + '/' + files[i],
                           dest_train + '/' + folder + '/' + files[i])  #Ccopy an image in the training set
    # Create validation set randomly
    for j in range(i + 1, int(len(files) * (validationSplit + trainingSplit))):
        dest = shutil.copy(cl + '/' + files[j],
                           dest_valid + '/' + folder + '/' + files[j])  # Copy an image in the validation set
    # Create test set randomly
    for k in range(j + 1, len(files)):
        dest = shutil.copy(cl + '/' + files[k],
                           dest_test + '/' + folder + '/' + files[k])  # Copy an image in the testing set
    # Below were present the part where we did undersampling, by random.shuffle() again and remove the number of file in excess

training_dir = 'temp_split/training'
validation_dir = 'temp_split/validation'
testing_dir = 'temp_split/testing'

# Obtain a data generator with the 'ImageDataGenerator.flow_from_directory' method
training_augmented = train_data_gen.flow_from_directory(directory=training_dir,
                                                          target_size=(96, 96),
                                                          color_mode='rgb',
                                                          classes=labels,
                                                          class_mode='categorical',
                                                          batch_size=batch_size,
                                                          shuffle=True,
                                                          seed=seed)


# Using also the validation augmented will affect the accuracy value, showing a higher accuracy
validation_augmented = valid_data_gen.flow_from_directory(directory=validation_dir,
                                                            target_size=(96, 96),
                                                            color_mode='rgb',
                                                            classes=labels,
                                                            class_mode='categorical',
                                                            batch_size=batch_size,
                                                            shuffle=True,
                                                            seed=seed)

testing_gen = valid_data_gen.flow_from_directory(directory=testing_dir,
                                                         target_size=(96, 96),
                                                         color_mode='rgb',
                                                         classes=labels,
                                                         class_mode='categorical',
                                                         batch_size=batch_size,
                                                         shuffle=False,
                                                         seed=seed)

# Compute class weights
class_weights = compute_class_weight(class_weight="balanced",
                                     classes=np.unique(training_augmented.classes),
                                     y=training_augmented.classes)
class_weights = dict(zip(np.unique(training_augmented.classes), class_weights))

input_shape = (96, 96, 3)
epochs = 120

supernet = tfk.applications.convnext.ConvNeXtBase(
    model_name='convnext_base',
    include_top=False,
    include_preprocessing=True,
    weights='imagenet',
    input_tensor=None,
    input_shape=input_shape,
    pooling=None,
    classifier_activation='softmax'
)
supernet.summary()

supernet.trainable = True
for layer in supernet.layers[:-70]:
    layer.trainable = False

tfk.utils.plot_model(supernet)

inputs = tfk.Input(shape=input_shape)
x = tfkl.GaussianNoise(0.1, seed=seed,input_shape=input_shape)(inputs)
x = supernet(x)
x = tfkl.GlobalAveragePooling2D()(x)
x = tfkl.LeakyReLU()(x)
x = tfkl.BatchNormalization()(x)
x = tfkl.Dense(
      1024,
      activation='relu',
      kernel_initializer = tfk.initializers.HeUniform(seed))(x)
x = tfkl.GaussianNoise(0.1, seed=seed)(x)
x = tfkl.LeakyReLU()(x)
x = tfkl.BatchNormalization()(x)
outputs = tfkl.Dense(
  len(labels),
  activation='softmax',
  kernel_initializer = tfk.initializers.GlorotUniform(seed))(x)

  # Connect input and output through the Model class
model = tfk.Model(inputs=inputs, outputs=outputs, name='model')

model.compile(loss=tfk.losses.CategoricalCrossentropy(), optimizer=tfk.optimizers.Adam(learning_rate=5e-5), metrics='accuracy')
# Compile the model
model.summary()

# Utility function to create folders and callbacks for training
def create_folders_and_callbacks(model_name):

  exps_dir = os.path.join('data_augmentation_experiments')
  if not os.path.exists(exps_dir):
      os.makedirs(exps_dir)

  now = datetime.now().strftime('%b%d_%H-%M-%S')

  exp_dir = os.path.join(exps_dir, model_name + '_' + str(now))
  if not os.path.exists(exp_dir):
      os.makedirs(exp_dir)

  callbacks = []

  # Early Stopping
  # --------------
  es_callback = tf.keras.callbacks.EarlyStopping(monitor='val_loss', patience=15, restore_best_weights=True)
  callbacks.append(es_callback)

  return callbacks

# Create folders and callbacks and fit
callbacks = create_folders_and_callbacks(model_name='CNN')

# Train the model
history_model = model.fit(
    x=training_augmented,
    batch_size=batch_size,
    epochs=epochs,
    #shuffle=True,
    validation_data=validation_augmented,
    callbacks=callbacks,
    class_weight=class_weights
).history

# Plot the training
plt.figure(figsize=(15,5))
plt.plot(history_model['loss'], label='Training', alpha=.3, color='#ff7f0e', linestyle='--')
plt.plot(history_model['val_loss'], label='Validation', alpha=.8, color='#ff7f0e')
plt.legend(loc='upper left')
plt.title('Categorical Crossentropy')
plt.grid(alpha=.3)

plt.figure(figsize=(15,5))
plt.plot(history_model['accuracy'], label='Training', alpha=.8, color='#ff7f0e', linestyle='--')
plt.plot(history_model['val_accuracy'], label='Validation', alpha=.8, color='#ff7f0e')
plt.legend(loc='upper left')
plt.title('Accuracy')
plt.grid(alpha=.3)

plt.show()

model.save("data_augmentation_experiments/TestCNN_convnext_base_transfer_learning_testing")
del model

# Re-load the model after transfer learning
ft_model = tfk.models.load_model('data_augmentation_experiments/TestCNN_convnext_base_transfer_learning_testing')
ft_model.summary()

# Set all layers to trainable = true
ft_model.get_layer('convnext_base').trainable = True
for i, layer in enumerate(ft_model.get_layer('convnext_base').layers):
   print(i, layer.name, layer.trainable)

# Note that the learning rate has been reduced during fine-tuning
ft_model.compile(loss=tfk.losses.CategoricalCrossentropy(), optimizer=tfk.optimizers.Adam(1e-6), metrics='accuracy')

fine_callbacks = []

# Early Stopping
# --------------
es_callback = tf.keras.callbacks.EarlyStopping(monitor='val_accuracy', patience=10, restore_best_weights=True)
fine_callbacks.append(es_callback)

history_model_ft = ft_model.fit(
    x=training_augmented,
    batch_size=batch_size,
    epochs=200,
    #shuffle=True,
    validation_data=validation_augmented,
    class_weight=class_weights,
    callbacks=fine_callbacks
).history

ft_model.save("data_augmentation_experiments/TestCNN_convnext_base_fine_tuning_testing")
del ft_model

# Plot the training
plt.figure(figsize=(15,5))
plt.plot(history_model_ft['loss'], label='Training', alpha=.3, color='#ff7f0e', linestyle='--')
plt.plot(history_model_ft['val_loss'], label='Validation', alpha=.8, color='#ff7f0e')
plt.legend(loc='upper left')
plt.title('Categorical Crossentropy')
plt.grid(alpha=.3)

plt.figure(figsize=(15,5))
plt.plot(history_model_ft['accuracy'], label='Training', alpha=.8, color='#ff7f0e', linestyle='--')
plt.plot(history_model_ft['val_accuracy'], label='Validation', alpha=.8, color='#ff7f0e')
plt.legend(loc='upper left')
plt.title('Accuracy')
plt.grid(alpha=.3)

plt.show()

model_t = tfk.models.load_model("data_augmentation_experiments/TestCNN_convnext_base_transfer_learning_testing")
model_t_test_metrics = model_t.evaluate(testing_gen, return_dict=True)
# Trained with data augmentation
model_f = tfk.models.load_model("data_augmentation_experiments/TestCNN_convnext_base_fine_tuning_testing")
model_f_test_metrics = model_f.evaluate(testing_gen, return_dict=True)

print()
print("Test metrics transfer learning")
print(model_t_test_metrics)
print("Test metrics fine tuning")
print(model_f_test_metrics)