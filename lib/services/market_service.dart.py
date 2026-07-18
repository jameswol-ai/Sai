import 'dart:math';

class MarketService {
  static final Map<String, double> _bases = {
    'UGX': 3800, 'KES': 130, 'TZS': 2600, 'SSP': 1600,
    'RWF': 1350, 'USD': 1, 'EUR': 0.92
  };

  static Map<String, double> getMarket() {
    final random = Random();
    return _bases.map((key, value) => MapEntry(key,
        double.parse((value + random.nextDouble() * 10 - 5).toStringAsFixed(2))));
  }
}
