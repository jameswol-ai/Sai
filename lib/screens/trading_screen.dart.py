import 'package:flutter/material.dart';
import '../services/supabase_service.dart';
import '../services/market_service.dart';

class TradingScreen extends StatefulWidget {
  final String username;
  final double risk;
  TradingScreen({required this.username, required this.risk});

  @override
  _TradingScreenState createState() => _TradingScreenState();
}

class _TradingScreenState extends State<TradingScreen> {
  String _selectedCurrency = 'UGX';
  String _action = 'BUY';

  void _execute() async {
    double price = MarketService.getMarket()[_selectedCurrency]!;
    double pnl = await SupabaseService.executeTrade(
      widget.username, _selectedCurrency, _action, price, widget.risk);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Trade executed. PnL: \$${pnl.toStringAsFixed(2)}')),
    );
  }

  @override
  Widget build(BuildContext context) {
    final rates = MarketService.getMarket();
    return Scaffold(
      appBar: AppBar(title: Text('Manual Trading'), backgroundColor: Colors.green[800]),
      body: Padding(
        padding: EdgeInsets.all(16),
        child: Column(
          children: [
            DropdownButtonFormField<String>(
              value: _selectedCurrency,
              items: rates.keys.map((e) => DropdownMenuItem(value: e, child: Text(e))).toList(),
              onChanged: (val) => setState(() { _selectedCurrency = val!; }),
              decoration: InputDecoration(labelText: 'Currency'),
            ),
            SizedBox(height: 20),
            Text('Current Price: ${rates[_selectedCurrency]}', style: TextStyle(fontSize: 20)),
            SizedBox(height: 20),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                ElevatedButton(
                  onPressed: () => setState(() { _action = 'BUY'; }),
                  child: Text('BUY'),
                  style: ElevatedButton.styleFrom(backgroundColor: _action == 'BUY' ? Colors.green : Colors.grey),
                ),
                ElevatedButton(
                  onPressed: () => setState(() { _action = 'SELL'; }),
                  child: Text('SELL'),
                  style: ElevatedButton.styleFrom(backgroundColor: _action == 'SELL' ? Colors.red : Colors.grey),
                ),
              ],
            ),
            SizedBox(height: 30),
            ElevatedButton.icon(
              onPressed: _execute,
              icon: Icon(Icons.flash_on),
              label: Text('Execute Trade'),
              style: ElevatedButton.styleFrom(minimumSize: Size(double.infinity, 50), backgroundColor: Colors.green),
            ),
          ],
        ),
      ),
    );
  }
}