import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:academic_comeback/main.dart';
import 'package:academic_comeback/features/catalog/views/product_detail_view.dart';

void main() {
  testWidgets('App smoke test loads catalog', (WidgetTester tester) async {
    await tester.pumpWidget(const ProviderScope(child: AcademicComebackApp()));
    await tester.pumpAndSettle();

    expect(find.text('SCALE GROUP'), findsOneWidget);
    expect(find.text('Masterclasses & Field Manuals'), findsOneWidget);
  });

  testWidgets('ProductDetailView renders Quitting The Handjob 4 pillars and chapters', (WidgetTester tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: ProductDetailView(slug: 'quitting-the-handjob'),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Quitting The Handjob'), findsOneWidget);
    expect(find.text('The 4 Recovery Pillars'), findsOneWidget);
    expect(find.text('8 Tactical Chapters'), findsOneWidget);
    expect(find.text('David Itoya'), findsOneWidget);
  });
}
