import 'package:flutter/material.dart';

class AppColors {
  static const Color background = Color(0xFF0B0F19);
  static const Color card = Color(0xFF131B2E);
  static const Color surface = Color(0xFF1E293B);
  static const Color gold = Color(0xFFD4AF37);
  static const Color lightGold = Color(0xFFF3E5AB);
  static const Color textPrimary = Color(0xFFE2E8F0);
  static const Color textMuted = Color(0xFF94A3B8);
  static const Color border = Color(0x33D4AF37);
  static const Color success = Color(0xFF10B981);
  static const Color error = Color(0xFFEF4444);

  static const LinearGradient goldGradient = LinearGradient(
    colors: [gold, lightGold],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );
}
