import 'package:go_router/go_router.dart';
import '../features/catalog/views/catalog_view.dart';
import '../features/catalog/views/product_detail_view.dart';
import '../features/library/views/library_view.dart';
import '../features/affiliate/views/affiliate_view.dart';

final appRouter = GoRouter(
  initialLocation: '/',
  routes: [
    GoRoute(
      path: '/',
      builder: (context, state) => const CatalogView(),
    ),
    GoRoute(
      path: '/product/:slug',
      builder: (context, state) {
        final slug = state.pathParameters['slug'] ?? '';
        return ProductDetailView(slug: slug);
      },
    ),
    GoRoute(
      path: '/library',
      builder: (context, state) => const LibraryView(),
    ),
    GoRoute(
      path: '/affiliate',
      builder: (context, state) => const AffiliateView(),
    ),
  ],
);
