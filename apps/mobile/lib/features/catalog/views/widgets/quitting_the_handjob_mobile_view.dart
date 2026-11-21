import 'package:flutter/material.dart';
import '../../../../core/constants/app_colors.dart';

class QuittingTheHandjobMobileView extends StatefulWidget {
  final VoidCallback onCheckout;

  const QuittingTheHandjobMobileView({super.key, required this.onCheckout});

  @override
  State<QuittingTheHandjobMobileView> createState() => _QuittingTheHandjobMobileViewState();
}

class _QuittingTheHandjobMobileViewState extends State<QuittingTheHandjobMobileView> {
  int _selectedPillar = 0;

  static const List<Map<String, dynamic>> _pillars = [
    {
      'num': '01',
      'tag': 'PILLAR 01 · NEUROBIOLOGY',
      'title': 'Dopamine Receptor Regeneration',
      'summary':
          'Understand the exact 30-day biological timeline required for your brain to regenerate downregulated D2 dopamine receptors, lifting chronic brain fog and restoring daily drive.',
      'color': Color(0xFFF59E0B),
      'icon': Icons.show_chart,
      'kpi': 'Key Outcome: D2 Receptor Resensitization',
      'items': [
        {'title': 'Delta-FosB Reversal', 'desc': 'Stop the hyper-stimulation cycle locking reward pathways in perpetual craving.'},
        {'title': 'The 30-Day Timeline', 'desc': 'Navigate the flatline phase with clear biological milestones instead of anxiety.'},
        {'title': 'Prefrontal Re-Command', 'desc': 'Restore executive rational control over primitive subconscious impulses.'},
      ],
    },
    {
      'num': '02',
      'tag': 'PILLAR 02 · EXECUTION',
      'title': 'The C.A.R.E. Framework',
      'summary':
          'Cue Disruption, Anxiety & Urge Surfing, Radical Environmental Friction, and Energetic State Shifting. Remove willpower from the equation entirely.',
      'color': Color(0xFF0284C7),
      'icon': Icons.security,
      'kpi': 'Key Outcome: Willpower-Free System Architecture',
      'items': [
        {'title': 'Cue Disruption', 'desc': 'Neutralize environmental and emotional triggers before cravings have power to ignite.'},
        {'title': 'Radical Friction', 'desc': 'Install insurmountable barriers between trigger moments and relapse devices.'},
        {'title': 'Urge Surfing', 'desc': 'Ride dopaminergic wave peaks to natural extinction without panic or white-knuckling.'},
      ],
    },
    {
      'num': '03',
      'tag': 'PILLAR 03 · CRISIS PROTOCOL',
      'title': 'The 5-Minute Emergency Intervention',
      'summary':
          'The step-by-step physiological kill switch to deploy the exact instant an urge peaks. Shuts off the dopaminergic loop before rational prefrontal cortex is overpowered.',
      'color': Color(0xFFDC2626),
      'icon': Icons.local_fire_department,
      'kpi': 'Key Outcome: 5-Min Kill Switch Deployment',
      'items': [
        {'title': 'Parasympathetic Reset', 'desc': 'Breathing sequences that immediately downshift acute sympathetic arousal.'},
        {'title': 'Temperature Shock', 'desc': 'Thermal reflex protocols that snap the mind out of compulsive dopamine trance.'},
        {'title': 'State Displacement', 'desc': 'Reroute blood flow away from the limbic system back to executive function.'},
      ],
    },
    {
      'num': '04',
      'tag': 'PILLAR 04 · IDENTITY',
      'title': 'Identity Deconstruction & Sublimation',
      'summary':
          'Stop identifying as a recovering addict fighting temptations. Shift into complete indifference, channel raw sexual energy into high-performance strength and business mastery.',
      'color': Color(0xFF16A34A),
      'icon': Icons.military_tech,
      'kpi': 'Key Outcome: Sovereign Self-Mastery',
      'items': [
        {'title': 'Identity Reset', 'desc': 'Eliminate streak-counting mentality and anchor baseline in unshakeable self-command.'},
        {'title': 'Sexual Transmutation', 'desc': 'Channel biological drive into heavy physical training, work output, and clear focus.'},
        {'title': 'Sovereign Presence', 'desc': 'Develop grounded masculine presence, deep voice cadence, and confident authority.'},
      ],
    },
  ];

  static const List<Map<String, String>> _chapters = [
    {'num': '01', 'title': 'The Dopamine Trap', 'desc': 'How modern pornography hacks evolutionary biological circuits and downregulates androgen receptors.'},
    {'num': '02', 'title': 'The Neurobiology of Relapse', 'desc': 'The delta-FosB accumulation cycle: why relying on willpower fails under stress.'},
    {'num': '03', 'title': 'The C.A.R.E. Protocol', 'desc': 'Engineering physical and digital environments to place insurmountable biological barriers.'},
    {'num': '04', 'title': 'The 5-Minute Emergency Protocol', 'desc': 'The precise physical protocol to execute when an urge hits. Temperature shock and respiratory pacing.'},
    {'num': '05', 'title': 'Dopamine Fasting & Receptor Regeneration', 'desc': 'What really happens in Days 1–7, 8–14, 15–30, and beyond. How to endure the flatline.'},
    {'num': '06', 'title': 'Sexual Energy Sublimation', 'desc': 'Directing aggressive biological drive into heavy lifting, business execution, and study stamina.'},
    {'num': '07', 'title': 'Conquering Emotional Triggers', 'desc': 'Dissecting the true roots of relapse: isolation, boredom, fatigue, and performance anxiety.'},
    {'num': '08', 'title': 'Sovereign Self-Mastery', 'desc': 'Building an unshakeable masculine frame, transforming vocal tone, eye contact, and self-respect.'},
  ];

  @override
  Widget build(BuildContext context) {
    final pillar = _pillars[_selectedPillar];
    final Color pillarColor = pillar['color'] as Color;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Editorial Quote Banner
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AppColors.card,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: AppColors.gold.withValues(alpha: 0.6), width: 1.5),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: const [
              Text(
                '“You are not failing because you lack discipline. You are failing because you are using moral willpower against an ancient neurobiological survival reflex.”',
                style: TextStyle(
                  color: Colors.white,
                  fontStyle: FontStyle.italic,
                  fontSize: 14,
                  height: 1.45,
                  fontWeight: FontWeight.w600,
                ),
              ),
              SizedBox(height: 8),
              Text(
                '— David Itoya, Author & Founder of Scale Group',
                style: TextStyle(color: AppColors.gold, fontSize: 11, fontWeight: FontWeight.bold),
              ),
            ],
          ),
        ),
        const SizedBox(height: 24),

        // 4 Core Pillars Section Header
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: const [
                Text(
                  'CORE ARCHITECTURE',
                  style: TextStyle(color: AppColors.lightGold, fontSize: 10, fontWeight: FontWeight.bold, letterSpacing: 1),
                ),
                SizedBox(height: 2),
                Text(
                  'The 4 Recovery Pillars',
                  style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                ),
              ],
            ),
            Text(
              '0${_selectedPillar + 1} / 04',
              style: const TextStyle(color: AppColors.gold, fontWeight: FontWeight.bold, fontSize: 13),
            ),
          ],
        ),
        const SizedBox(height: 12),

        // Pillar Tab Selectors
        Row(
          children: List.generate(_pillars.length, (idx) {
            final isSelected = _selectedPillar == idx;
            final p = _pillars[idx];
            final color = p['color'] as Color;
            return Expanded(
              child: GestureDetector(
                onTap: () => setState(() => _selectedPillar = idx),
                child: Container(
                  margin: EdgeInsets.only(right: idx < _pillars.length - 1 ? 6 : 0),
                  padding: const EdgeInsets.symmetric(vertical: 8),
                  decoration: BoxDecoration(
                    color: isSelected ? color.withValues(alpha: 0.2) : AppColors.card,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: isSelected ? color : Colors.white.withValues(alpha: 0.08)),
                  ),
                  child: Center(
                    child: Text(
                      'Pillar ${p['num']}',
                      style: TextStyle(
                        color: isSelected ? Colors.white : AppColors.textMuted,
                        fontSize: 11,
                        fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                      ),
                    ),
                  ),
                ),
              ),
            );
          }),
        ),
        const SizedBox(height: 14),

        // Active Pillar Card
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AppColors.card,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: pillarColor.withValues(alpha: 0.6), width: 1.5),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(pillar['icon'] as IconData, color: pillarColor, size: 20),
                  const SizedBox(width: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(
                      color: pillarColor.withValues(alpha: 0.2),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      pillar['tag'] as String,
                      style: TextStyle(color: pillarColor, fontSize: 10, fontWeight: FontWeight.bold),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Text(
                pillar['title'] as String,
                style: const TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 6),
              Text(
                pillar['summary'] as String,
                style: const TextStyle(color: AppColors.textPrimary, fontSize: 13, height: 1.4),
              ),
              const SizedBox(height: 14),

              // Deliverables List
              ...((pillar['items'] as List<Map<String, String>>).map((item) {
                return Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(Icons.check_circle, size: 16, color: AppColors.success),
                      const SizedBox(width: 8),
                      Expanded(
                        child: RichText(
                          text: TextSpan(
                            style: const TextStyle(color: AppColors.textPrimary, fontSize: 12, height: 1.3),
                            children: [
                              TextSpan(text: '${item['title']}: ', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                              TextSpan(text: item['desc']),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                );
              })),
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: AppColors.success.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.verified, size: 14, color: AppColors.success),
                    const SizedBox(width: 6),
                    Text(
                      pillar['kpi'] as String,
                      style: const TextStyle(color: AppColors.success, fontSize: 11, fontWeight: FontWeight.bold),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 28),

        // Chapters Curriculum
        const Text(
          'WHAT YOU WILL MASTER',
          style: TextStyle(color: AppColors.lightGold, fontSize: 10, fontWeight: FontWeight.bold, letterSpacing: 1),
        ),
        const SizedBox(height: 2),
        const Text(
          '8 Tactical Chapters',
          style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 12),
        ..._chapters.map((ch) {
          return Container(
            margin: const EdgeInsets.only(bottom: 10),
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: AppColors.card,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.white.withValues(alpha: 0.06)),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
                  decoration: BoxDecoration(
                    color: AppColors.gold.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    'CH ${ch['num']}',
                    style: const TextStyle(color: AppColors.gold, fontSize: 10, fontWeight: FontWeight.bold),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        ch['title']!,
                        style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        ch['desc']!,
                        style: const TextStyle(color: AppColors.textMuted, fontSize: 12, height: 1.3),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          );
        }),
        const SizedBox(height: 24),

        // Two Choices Crossroads
        const Text(
          'TWO CHOICES CROSSROADS',
          style: TextStyle(color: AppColors.lightGold, fontSize: 10, fontWeight: FontWeight.bold, letterSpacing: 1),
        ),
        const SizedBox(height: 2),
        const Text(
          'Your Decision Today',
          style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 12),
        // Path 1
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AppColors.error.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: AppColors.error.withValues(alpha: 0.3)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: const [
              Text(
                'PATH 1: THE COST OF INACTION',
                style: TextStyle(color: AppColors.error, fontSize: 11, fontWeight: FontWeight.bold, letterSpacing: 0.5),
              ),
              SizedBox(height: 6),
              Text(
                'Stay in the Hidden Loop',
                style: TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold),
              ),
              SizedBox(height: 6),
              Text(
                'Close this screen. Rely on willpower again. Within 72 hours, boredom or stress triggers relapse. You face the familiar brain fog, reduced motivation, and the agonizing sense that you are failing yourself in private.',
                style: TextStyle(color: AppColors.textPrimary, fontSize: 12, height: 1.4),
              ),
            ],
          ),
        ),
        const SizedBox(height: 10),
        // Path 2
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AppColors.card,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: AppColors.gold, width: 1.5),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: const [
              Text(
                'PATH 2: SOVEREIGN MASTERY',
                style: TextStyle(color: AppColors.gold, fontSize: 11, fontWeight: FontWeight.bold, letterSpacing: 0.5),
              ),
              SizedBox(height: 6),
              Text(
                'Install a Clinical Recovery System',
                style: TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold),
              ),
              SizedBox(height: 6),
              Text(
                'Invest ₦5,000 today. Master the C.A.R.E. protocol and deploy the 5-Minute Kill Switch. Re-sensitize your dopamine receptors and walk with the quiet, masculine presence of a man in total command.',
                style: TextStyle(color: AppColors.textPrimary, fontSize: 12, height: 1.4),
              ),
            ],
          ),
        ),
        const SizedBox(height: 24),

        // Author Bio Card
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AppColors.card,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: const [
              Text(
                'ABOUT THE AUTHOR',
                style: TextStyle(color: AppColors.lightGold, fontSize: 10, fontWeight: FontWeight.bold, letterSpacing: 1),
              ),
              SizedBox(height: 6),
              Text(
                'David Itoya',
                style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
              ),
              Text(
                'Author & Founder, Scale Group',
                style: TextStyle(color: AppColors.gold, fontSize: 12, fontWeight: FontWeight.w600),
              ),
              SizedBox(height: 10),
              Text(
                '“I spent years watching exceptionally talented, ambitious young men slowly destroy their drive and self-esteem through private compulsive habits. Quitting The Handjob was engineered to replace helpless willpower with a clinical neurobiological battle plan.”',
                style: TextStyle(color: AppColors.textMuted, fontSize: 12, height: 1.4, fontStyle: FontStyle.italic),
              ),
            ],
          ),
        ),
        const SizedBox(height: 24),
      ],
    );
  }
}
