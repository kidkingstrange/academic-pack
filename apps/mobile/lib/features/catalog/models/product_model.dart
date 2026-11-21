class ProductModel {
  final String id;
  final String slug;
  final String title;
  final String description;
  final int priceNaira;
  final int regularPriceNaira;
  final double priceUsd;
  final double regularPriceUsd;
  final String category;
  final List<String> benefits;
  final List<String> features;
  final bool isBundle;

  const ProductModel({
    required this.id,
    required this.slug,
    required this.title,
    required this.description,
    required this.priceNaira,
    required this.regularPriceNaira,
    required this.priceUsd,
    required this.regularPriceUsd,
    required this.category,
    required this.benefits,
    required this.features,
    this.isBundle = false,
  });

  factory ProductModel.fromJson(Map<String, dynamic> json) {
    return ProductModel(
      id: json['id'] as String? ?? '',
      slug: json['slug'] as String? ?? '',
      title: json['title'] as String? ?? '',
      description: json['description'] as String? ?? '',
      priceNaira: json['price_naira'] as int? ?? 5000,
      regularPriceNaira: json['regular_price_naira'] as int? ?? 20000,
      priceUsd: (json['price_usd'] as num?)?.toDouble() ?? 15.0,
      regularPriceUsd: (json['regular_price_usd'] as num?)?.toDouble() ?? 40.0,
      category: json['category'] as String? ?? 'General',
      benefits: (json['benefits'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      features: (json['features'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      isBundle: json['is_bundle'] as bool? ?? false,
    );
  }
}
