"""Tests for the filters module."""

import pytest
import numpy as np
from visualizador.filters import BaselineEMA


class TestBaselineEMA:
    """Test cases for BaselineEMA filter."""

    def test_initialization(self):
        """Test filter initialization."""
        alpha = 0.9
        filter_obj = BaselineEMA(alpha=alpha)
        assert filter_obj.alpha == alpha
        assert filter_obj.baseline is None

    def test_process_sample_first_sample(self):
        """Test processing the first sample."""
        filter_obj = BaselineEMA(alpha=0.5)
        voltage = 1.0
        filtered, baseline = filter_obj.process_sample(voltage)
        assert filtered == 0.0  # First sample, baseline = voltage, filtered = voltage - baseline = 0
        assert baseline == voltage

    def test_process_sample_subsequent_samples(self):
        """Test processing subsequent samples."""
        filter_obj = BaselineEMA(alpha=0.5)
        # First sample
        filtered1, baseline1 = filter_obj.process_sample(1.0)
        assert filtered1 == 0.0
        assert baseline1 == 1.0

        # Second sample
        filtered2, baseline2 = filter_obj.process_sample(2.0)
        expected_baseline = 0.5 * 1.0 + 0.5 * 2.0  # alpha * old_baseline + (1-alpha) * voltage
        expected_filtered = 2.0 - expected_baseline
        assert baseline2 == pytest.approx(expected_baseline)
        assert filtered2 == pytest.approx(expected_filtered)

    def test_baseline_convergence(self):
        """Test that baseline converges to constant input."""
        filter_obj = BaselineEMA(alpha=0.1)
        constant_voltage = 5.0

        # Process many samples
        for _ in range(100):
            filtered, baseline = filter_obj.process_sample(constant_voltage)

        # After many iterations, baseline should be close to input
        assert baseline == pytest.approx(constant_voltage, abs=0.01)
        assert filtered == pytest.approx(0.0, abs=0.01)