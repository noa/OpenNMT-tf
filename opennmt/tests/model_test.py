# -*- coding: utf-8 -*-

import os
import six

from parameterized import parameterized
from numbers import Number

import tensorflow as tf
import numpy as np

from opennmt import decoders
from opennmt import encoders
from opennmt import inputters
from opennmt import models
from opennmt.models import catalog
from opennmt.tests import test_util


def _seq2seq_model(mode):
  model = models.SequenceToSequence(
      inputters.WordEmbedder(16),
      inputters.WordEmbedder(16),
      encoders.SelfAttentionEncoder(2, 16, 4, 32),
      decoders.SelfAttentionDecoder(2, 16, 4, 32))
  params = {}
  if mode == tf.estimator.ModeKeys.TRAIN:
    params["optimizer"] = "SGD"
    params["learning_rate"] = 0.1
  return model, params


class ModelTest(tf.test.TestCase):

  def _makeToyEnDeData(self, with_alignments=False):
    data_config = {}
    features_file = test_util.make_data_file(
        os.path.join(self.get_temp_dir(), "src.txt"),
        ["Parliament Does Not Support Amendment Freeing Tymoshenko",
         "Today , the Ukraine parliament dismissed , within the Code of Criminal Procedure "
         "amendment , the motion to revoke an article based on which the opposition leader , "
         "Yulia Tymoshenko , was sentenced .",
         "The amendment that would lead to freeing the imprisoned former Prime Minister was "
         "revoked during second reading of the proposal for mitigation of sentences for "
         "economic offences ."])
    labels_file = test_util.make_data_file(
        os.path.join(self.get_temp_dir(), "tgt.txt"),
        ["Keine befreiende Novelle für Tymoshenko durch das Parlament",
         "Das ukrainische Parlament verweigerte heute den Antrag , im Rahmen einer Novelle "
         "des Strafgesetzbuches denjenigen Paragrafen abzuschaffen , auf dessen Grundlage die "
         "Oppositionsführerin Yulia Timoshenko verurteilt worden war .",
         "Die Neuregelung , die den Weg zur Befreiung der inhaftierten Expremierministerin hätte "
         "ebnen können , lehnten die Abgeordneten bei der zweiten Lesung des Antrags auf Milderung "
         "der Strafen für wirtschaftliche Delikte ab ."])
    data_config["source_vocabulary"] = test_util.make_vocab_from_file(
        os.path.join(self.get_temp_dir(), "src_vocab.txt"), features_file)
    data_config["target_vocabulary"] = test_util.make_vocab_from_file(
        os.path.join(self.get_temp_dir(), "tgt_vocab.txt"), labels_file)
    if with_alignments:
      # Dummy and incomplete alignments.
      data_config["train_alignments"] = test_util.make_data_file(
          os.path.join(self.get_temp_dir(), "aligne.txt"),
          ["0-0 1-0 2-2 3-4 4-4 5-6",
           "0-1 1-1 1-3 2-3 4-4",
           "0-0 1-0 2-2 3-4 4-4 5-6"])
    return features_file, labels_file, data_config

  def _makeToyLMData(self):
    features_file, _, data_config = self._makeToyEnDeData()
    return features_file, {"vocabulary": data_config["source_vocabulary"]}

  def _makeToyTaggerData(self):
    data_config = {}
    features_file = test_util.make_data_file(
        os.path.join(self.get_temp_dir(), "src.txt"),
        ["M . Smith went to Washington .",
         "I live in New Zealand ."])
    labels_file = test_util.make_data_file(
        os.path.join(self.get_temp_dir(), "labels.txt"),
        ["B-PER I-PER E-PER O O S-LOC O",
         "O O O B-LOC E-LOC O"])
    data_config["source_vocabulary"] = test_util.make_vocab_from_file(
        os.path.join(self.get_temp_dir(), "src_vocab.txt"), features_file)
    data_config["target_vocabulary"] = test_util.make_data_file(
        os.path.join(self.get_temp_dir(), "labels_vocab.txt"),
        ["O", "B-LOC", "I-LOC", "E-LOC", "S-LOC", "B-PER", "I-PER", "E-PER", "S-PER"])
    return features_file, labels_file, data_config

  def _makeToyClassifierData(self):
    data_config = {}
    features_file = test_util.make_data_file(
        os.path.join(self.get_temp_dir(), "src.txt"),
        ["This product was not good at all , it broke on the first use !",
         "Perfect , it does everything I need .",
         "How do I change the battery ?"])
    labels_file = test_util.make_data_file(
        os.path.join(self.get_temp_dir(), "labels.txt"), ["negative", "positive", "neutral"])
    data_config["source_vocabulary"] = test_util.make_vocab_from_file(
        os.path.join(self.get_temp_dir(), "src_vocab.txt"), features_file)
    data_config["target_vocabulary"] = test_util.make_data_file(
        os.path.join(self.get_temp_dir(), "labels_vocab.txt"), ["negative", "positive", "neutral"])
    return features_file, labels_file, data_config

  def _testGenericModel(self,
                        model,
                        mode,
                        features_file,
                        labels_file=None,
                        data_config=None,
                        batch_size=16,
                        prediction_heads=None,
                        metrics=None,
                        params=None):
    # Mainly test that the code does not throw.
    if params is None:
      params = model.auto_config()["params"]
    if data_config is None:
      data_config = {}
    model.initialize(data_config, params=params)
    if mode == tf.estimator.ModeKeys.PREDICT:
      dataset = model.examples_inputter.make_inference_dataset(
          features_file, batch_size)
    elif mode == tf.estimator.ModeKeys.EVAL:
      dataset = model.examples_inputter.make_evaluation_dataset(
          features_file, labels_file, batch_size)
    elif mode == tf.estimator.ModeKeys.TRAIN:
      dataset = model.examples_inputter.make_training_dataset(
          features_file, labels_file, batch_size)
    data = iter(dataset).next()
    if mode != tf.estimator.ModeKeys.PREDICT:
      features, labels = data
    else:
      features, labels = data, None
    outputs, predictions = model(features, labels=labels, mode=mode)
    if mode != tf.estimator.ModeKeys.PREDICT:
      loss = model.compute_loss(outputs, labels, training=mode == tf.estimator.ModeKeys.TRAIN)
      if mode == tf.estimator.ModeKeys.EVAL:
        eval_metrics = model.get_metrics()
        if eval_metrics is not None:
          model.update_metrics(eval_metrics, predictions, labels)
          for metric in metrics:
            self.assertIn(metric, eval_metrics)
    else:
      self.assertIsInstance(predictions, dict)
      if prediction_heads is not None:
        for head in prediction_heads:
          self.assertIn(head, predictions)

  @parameterized.expand([
      [tf.estimator.ModeKeys.TRAIN],
      [tf.estimator.ModeKeys.EVAL],
      [tf.estimator.ModeKeys.PREDICT]])
  def testSequenceToSequence(self, mode):
    model, params = _seq2seq_model(mode)
    features_file, labels_file, data_config = self._makeToyEnDeData()
    self._testGenericModel(
        model,
        mode,
        features_file,
        labels_file,
        data_config,
        prediction_heads=["tokens", "length", "log_probs"],
        params=params)

  @parameterized.expand([["ce"], ["mse"]])
  def testSequenceToSequenceWithGuidedAlignment(self, ga_type):
    mode = tf.estimator.ModeKeys.TRAIN
    model, params = _seq2seq_model(mode)
    params["guided_alignment_type"] = ga_type
    features_file, labels_file, data_config = self._makeToyEnDeData(with_alignments=True)
    model.initialize(data_config, params=params)
    with tf.Graph().as_default():
      dataset = model.examples_inputter.make_training_dataset(features_file, labels_file, 16)
      iterator = tf.compat.v1.data.make_initializable_iterator(dataset)
      features, labels = iterator.get_next()
      self.assertIn("alignment", labels)
      outputs, _ = model(features, labels=labels, mode=mode)
      loss = model.compute_loss(outputs, labels, training=True)
      loss = loss[0] / loss[1]
      with self.session() as sess:
        sess.run(tf.compat.v1.global_variables_initializer())
        sess.run(tf.compat.v1.local_variables_initializer())
        sess.run(tf.compat.v1.tables_initializer())
        sess.run(iterator.initializer)
        loss = sess.run(loss)
        self.assertIsInstance(loss, Number)

  def testSequenceToSequenceWithReplaceUnknownTarget(self):
    mode = tf.estimator.ModeKeys.PREDICT
    model, params = _seq2seq_model(mode)
    params["replace_unknown_target"] = True
    features_file, labels_file, data_config = self._makeToyEnDeData()
    model.initialize(data_config)
    with tf.Graph().as_default():
      dataset = model.examples_inputter.make_inference_dataset(features_file, 16)
      iterator = tf.compat.v1.data.make_initializable_iterator(dataset)
      features = iterator.get_next()
      _, predictions = model(features)
      with self.session() as sess:
        sess.run(tf.compat.v1.global_variables_initializer())
        sess.run(tf.compat.v1.local_variables_initializer())
        sess.run(tf.compat.v1.tables_initializer())
        sess.run(iterator.initializer)
        _ = sess.run(predictions)

  def testSequenceToSequenceServing(self):
    # Test that serving features can be forwarded into the model.
    mode = tf.estimator.ModeKeys.PREDICT
    _, _, data_config = self._makeToyEnDeData()
    model, params = _seq2seq_model(mode)
    model.initialize(data_config, params=params)
    function = model.serve_function()
    function.get_concrete_function()

  @parameterized.expand([
      [tf.estimator.ModeKeys.TRAIN],
      [tf.estimator.ModeKeys.EVAL],
      [tf.estimator.ModeKeys.PREDICT]])
  def testLanguageModel(self, mode):
    # Mainly test that the code does not throw.
    decoder = decoders.SelfAttentionDecoder(
        2, num_units=16, num_heads=4, ffn_inner_dim=32, num_sources=0)
    model = models.LanguageModel(decoder, embedding_size=16)
    features_file, data_config = self._makeToyLMData()
    params = {
        "optimizer": "SGD",
        "learning_rate": 0.1}
    self._testGenericModel(
        model,
        mode,
        features_file,
        data_config=data_config,
        batch_size=1 if mode == tf.estimator.ModeKeys.PREDICT else 16,
        prediction_heads=["tokens", "length"],
        params=params)

  @parameterized.expand([
      [tf.estimator.ModeKeys.TRAIN],
      [tf.estimator.ModeKeys.EVAL],
      [tf.estimator.ModeKeys.PREDICT]])
  def testSequenceTagger(self, mode):
    model = models.SequenceTagger(inputters.WordEmbedder(10), encoders.MeanEncoder())
    features_file, labels_file, data_config = self._makeToyTaggerData()
    data_config["tagging_scheme"] = "bioes"
    params = {
        "optimizer": "SGD",
        "learning_rate": 0.1}
    self._testGenericModel(
        model,
        mode,
        features_file,
        labels_file,
        data_config,
        prediction_heads=["tags", "length"],
        metrics=["accuracy", "precision", "recall", "f1"],
        params=params)

  @parameterized.expand([
      [tf.estimator.ModeKeys.TRAIN],
      [tf.estimator.ModeKeys.EVAL],
      [tf.estimator.ModeKeys.PREDICT]])
  def testSequenceClassifier(self, mode):
    model = models.SequenceClassifier(inputters.WordEmbedder(10), encoders.MeanEncoder())
    features_file, labels_file, data_config = self._makeToyClassifierData()
    params = {
        "optimizer": "SGD",
        "learning_rate": 0.1}
    self._testGenericModel(
        model,
        mode,
        features_file,
        labels_file,
        data_config,
        prediction_heads=["classes"],
        metrics=["accuracy"],
        params=params)

  def testCreateVariables(self):
    _, _, data_config = self._makeToyEnDeData()
    model, params = _seq2seq_model(tf.estimator.ModeKeys.PREDICT)
    model.initialize(data_config, params=params)
    model.create_variables()
    self.assertTrue(len(model.trainable_variables) > 0)

  def testFreezeLayers(self):
    model, _ = _seq2seq_model(tf.estimator.ModeKeys.TRAIN)
    params = {"freeze_layers": ["decoder/output_layer", "encoder/layers/0"]}
    _, _, data_config = self._makeToyEnDeData()
    model.initialize(data_config, params=params)
    model.create_variables()
    trainable_variables = model.trainable_variables
    self.assertNotEmpty(trainable_variables)

    def _assert_layer_not_trainable(layer):
      self.assertFalse(layer.trainable)
      for variable in layer.variables:
        self.assertNotIn(variable, trainable_variables)

    _assert_layer_not_trainable(model.decoder.output_layer)
    _assert_layer_not_trainable(model.encoder.layers[0])

  def testTransferWeightsNewVocab(self):

    def _make_model(name, src_vocab, tgt_vocab, random_slots=False):
      model, _ = _seq2seq_model(tf.estimator.ModeKeys.TRAIN)
      optimizer = tf.keras.optimizers.Adam()
      data = {}
      data["source_vocabulary"] = test_util.make_data_file(
          os.path.join(self.get_temp_dir(), "%s-src-vocab.txt" % name),
          src_vocab)
      data["target_vocabulary"] = test_util.make_data_file(
          os.path.join(self.get_temp_dir(), "%s-tgt-vocab.txt" % name),
          tgt_vocab)
      model.initialize(data)
      model.create_variables(optimizer=optimizer)
      if random_slots:
        for variable in model.trainable_variables:
          for slot_name in optimizer.get_slot_names():
            slot = optimizer.get_slot(variable, slot_name)
            slot.assign(tf.random.uniform(slot.shape))
      return model, optimizer

    model_a, optimizer_a = _make_model(
        "a", ["a", "b", "c", "d", "e"], ["1", "2", "3", "4", "5", "6"], random_slots=True)
    model_b, optimizer_b = _make_model(
        "b", ["c", "a", "e", "f"], ["1", "3", "2", "6", "7"])
    src_mapping = [2, 0, 4, -1]
    tgt_mapping = [0, 2, 1, 5, -1]

    def _check_weight(weight_a, weight_b, mapping, vocab_axis=0):
      weight_a = self.evaluate(weight_a)
      weight_b = self.evaluate(weight_b)
      if vocab_axis != 0:
        perm = list(range(len(weight_a.shape)))
        perm[0], perm[vocab_axis] = perm[vocab_axis], perm[0]
        weight_a = np.transpose(weight_a, axes=perm)
        weight_b = np.transpose(weight_b, axes=perm)
      self.assertEqual(weight_b.shape[0], len(mapping) + 1)
      for index_b, index_a in enumerate(mapping):
        if index_a >= 0:
          self.assertAllEqual(weight_b[index_b], weight_a[index_a])

    def _check_weight_and_slots(weight_fn, mapping, vocab_axis=0):
      weight_a = weight_fn(model_a)
      weight_b = weight_fn(model_b)
      _check_weight(weight_a, weight_b, mapping, vocab_axis=vocab_axis)
      for slot_name in optimizer_b.get_slot_names():
        slot_a = optimizer_a.get_slot(weight_a, slot_name)
        slot_b = optimizer_b.get_slot(weight_b, slot_name)
        _check_weight(slot_a, slot_b, mapping, vocab_axis=vocab_axis)

    model_a.transfer_weights(model_b, new_optimizer=optimizer_b, optimizer=optimizer_a)
    _check_weight_and_slots(
        lambda model: model.features_inputter.embedding, src_mapping)
    _check_weight_and_slots(
        lambda model: model.labels_inputter.embedding, tgt_mapping)
    _check_weight_and_slots(
        lambda model: model.decoder.output_layer.bias, tgt_mapping)
    _check_weight_and_slots(
        lambda model: model.decoder.output_layer.kernel, tgt_mapping, vocab_axis=1)


if __name__ == "__main__":
  tf.test.main()
