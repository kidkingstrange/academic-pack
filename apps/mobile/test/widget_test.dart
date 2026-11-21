import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:academic_comeback/main.dart';

void main() {
  testWidgets('App smoke test loads catalog', (WidgetTester tester) async {
    await tester.pumpWidget(const ProviderScope(child: AcademicComebackApp()));
    await tester.pumpAndSettle();

    expect(find.text('SCALE GROUP'), findsOneWidget);
    expect(find.text('Masterclasses & Field Manuals'), findsOneWidget);
  });
}
