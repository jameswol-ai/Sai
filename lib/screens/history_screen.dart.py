import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../services/supabase_service.dart';
import '../models/trade.dart';

class HistoryScreen extends StatefulWidget {
  final String username;
  HistoryScreen({required this.username});

  @override
  _HistoryScreenState createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  late Future<List<Trade>> _tradesFuture;

  @override
  void initState() {
    super.initState();
    _tradesFuture = SupabaseService.getTradeHistory(widget.username);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Trade History'), backgroundColor: Colors.green[800]),
      body: FutureBuilder<List<Trade>>(
        future: _tradesFuture,
        builder: (ctx, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) return Center(child: CircularProgressIndicator());
          if (!snapshot.hasData || snapshot.data!.isEmpty) return Center(child: Text('No trades yet'));
          final trades = snapshot.data!;
          double totalPnl = trades.fold(0, (sum, t) => sum + t.pnl);
          return Column(
            children: [
              Padding(
                padding: EdgeInsets.all(16),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceAround,
                  children: [
                    Text('Trades: ${trades.length}', style: TextStyle(color: Colors.white)),
                    Text('Total PnL: \$${totalPnl.toStringAsFixed(2)}', style: TextStyle(color: totalPnl >= 0 ? Colors.green : Colors.red)),
                  ],
                ),
              ),
              Expanded(
                child: ListView.builder(
                  itemCount: trades.length,
                  itemBuilder: (ctx, i) {
                    Trade t = trades[i];
                    return ListTile(
                      title: Text('${t.action} ${t.symbol} @ ${t.price}'),
                      subtitle: Text(t.time),
                      trailing: Text('\$${t.pnl.toStringAsFixed(2)}', style: TextStyle(color: t.pnl >= 0 ? Colors.green : Colors.red)),
                    );
                  },
                ),
              ),
              // Cumulative PnL Chart
              SizedBox(height: 200, child: _buildPnLChart(trades)),
            ],
          );
        },
      ),
    );
  }

  Widget _buildPnLChart(List<Trade> trades) {
    final reversed = trades.reversed.toList();
    double cumulative = 0;
    List<FlSpot> spots = [];
    for (int i = 0; i < reversed.length; i++) {
      cumulative += reversed[i].pnl;
      spots.add(FlSpot(i.toDouble(), cumulative));
    }
    return LineChart(
      LineChartData(
        lineBarsData: [
          LineChartBarData(spots: spots, isCurved: true, color: Colors.green, barWidth: 2),
        ],
        titlesData: FlTitlesData(show: false),
        gridData: FlGridData(show: false),
        borderData: FlBorderData(show: false),
      ),
    );
  }
}