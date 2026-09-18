import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:in_app_purchase/in_app_purchase.dart';

import 'support_links.dart';

/// Where the tips stand: nothing asked yet, asking the store, ready with
/// products, no store or no products, a purchase in flight, a purchase
/// completed, or the last purchase failed.
enum TipStatus { idle, loading, ready, unavailable, purchasing, thanked }

/// Tips through the store's billing, for store builds ([usesStoreTips]).
/// One instance for the process: the purchase stream must be listened to
/// from launch, because a purchase interrupted by a crash or a pending
/// payment is delivered on the next start. Consumables: every tip can be
/// given again; nothing is restored. Wording rule as everywhere in
/// Support: "tip" and "support", never "donation" (docs/plan.md, D4).
class TipStore extends ChangeNotifier {
  TipStore._();

  static final TipStore instance = TipStore._();

  final InAppPurchase _iap = InAppPurchase.instance;
  StreamSubscription<List<PurchaseDetails>>? _purchases;

  TipStatus status = TipStatus.idle;
  List<ProductDetails> products = const [];

  /// The last thing worth telling the person: a thank-you, or why a
  /// purchase did not go through. Cleared by the next attempt.
  String? message;

  /// Whether the Support band and screen have anything to sell.
  bool get available => products.isNotEmpty;

  /// Asks the store once. Safe to call again; later calls do nothing.
  Future<void> load() async {
    if (!usesStoreTips || status != TipStatus.idle) return;
    status = TipStatus.loading;
    notifyListeners();
    try {
      _purchases ??= _iap.purchaseStream.listen(
        _onPurchases,
        onError: (Object e) => debugPrint('tips: purchase stream error: $e'),
      );
      if (!await _iap.isAvailable()) {
        debugPrint('tips: store not available');
        status = TipStatus.unavailable;
        notifyListeners();
        return;
      }
      final ids = tipProducts.keys.toSet();
      final response = await _iap.queryProductDetails(ids);
      products = [...response.productDetails]
        ..sort((a, b) => a.rawPrice.compareTo(b.rawPrice));
      final missing = response.notFoundIDs;
      debugPrint(
        'tips: ${products.length} products'
        '${missing.isEmpty ? '' : ', not found: $missing'}',
      );
      status = products.isEmpty ? TipStatus.unavailable : TipStatus.ready;
    } catch (e) {
      debugPrint('tips: $e');
      status = TipStatus.unavailable;
    }
    notifyListeners();
  }

  /// Opens the store's own purchase sheet for [product]. What happens next
  /// arrives on the purchase stream.
  Future<void> buy(ProductDetails product) async {
    message = null;
    status = TipStatus.purchasing;
    notifyListeners();
    try {
      // autoConsume (the default) consumes on Android so the same tip can
      // be bought again; iOS consumables need no such step.
      await _iap.buyConsumable(
        purchaseParam: PurchaseParam(productDetails: product),
      );
    } catch (e) {
      debugPrint('tips: could not start a purchase: $e');
      message = 'The store could not start the purchase.';
      status = TipStatus.ready;
      notifyListeners();
    }
  }

  Future<void> _onPurchases(List<PurchaseDetails> purchases) async {
    for (final purchase in purchases) {
      debugPrint('tips: ${purchase.productID} ${purchase.status.name}');
      switch (purchase.status) {
        case PurchaseStatus.pending:
          status = TipStatus.purchasing;
        case PurchaseStatus.purchased:
        case PurchaseStatus.restored:
          status = TipStatus.thanked;
          message = 'Thank you. Your tip went through.';
        case PurchaseStatus.error:
          status = TipStatus.ready;
          message = purchase.error?.message.isNotEmpty == true
              ? 'The purchase did not go through: ${purchase.error!.message}'
              : 'The purchase did not go through.';
        case PurchaseStatus.canceled:
          status = TipStatus.ready;
      }
      // Every delivered purchase is acknowledged, or the store retries it
      // and (on Android) refunds it after three days.
      if (purchase.pendingCompletePurchase) {
        await _iap.completePurchase(purchase);
      }
    }
    notifyListeners();
  }
}
