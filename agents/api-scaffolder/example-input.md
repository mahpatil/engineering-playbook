# api-scaffolder — Example Input

## Invocation

Scaffold the Orders API for a Java Spring Boot service with two resources: Order and OrderLineItem.

---

## Request

```
API_NAME: Orders API
SERVICE_NAME: order-service
BASE_PATH: /api/v1
LANGUAGE: java
FRAMEWORK: springboot
PACKAGE_BASE: com.acme.orders

RESOURCES:
  - name: Order
    plural: orders
    fields:
      - name: id
        type: string
        required: false
        description: "Unique order identifier (UUID)"
      - name: customerId
        type: string
        required: true
        description: "Identifier of the customer placing the order"
      - name: status
        type: string
        required: false
        description: "Current order status: PENDING, CONFIRMED, CANCELLED, FULFILLED"
      - name: total
        type: object
        required: false
        description: "Total order value"
        fields:
          - name: amount
            type: string
            description: "Monetary amount as decimal string, e.g. '149.99'"
          - name: currency
            type: string
            description: "ISO 4217 currency code, e.g. 'USD'"
      - name: createdAt
        type: string
        required: false
        description: "ISO 8601 UTC creation timestamp"
      - name: updatedAt
        type: string
        required: false
        description: "ISO 8601 UTC last updated timestamp"
    operations: [list, get, create, delete]
    custom_actions:
      - name: confirm
        method: POST
        description: "Confirm a pending order after payment authorisation. Transitions order from PENDING to CONFIRMED."
      - name: cancel
        method: POST
        description: "Cancel an order. Only allowed when status is PENDING or CONFIRMED."

  - name: OrderLineItem
    plural: line-items
    parent: Order
    fields:
      - name: id
        type: string
        required: false
        description: "Line item identifier"
      - name: productId
        type: string
        required: true
        description: "Product identifier"
      - name: quantity
        type: integer
        required: true
        description: "Number of units ordered, minimum 1"
      - name: unitPrice
        type: object
        required: false
        description: "Unit price at time of order"
        fields:
          - name: amount
            type: string
          - name: currency
            type: string
    operations: [list, get, create, delete]

SCOPES:
  - name: orders:read
    description: "Read order data"
  - name: orders:write
    description: "Create, modify, and cancel orders"
  - name: orders:admin
    description: "Administrative operations including forced cancellation"

ERROR_TYPES:
  - type: order-not-found
    title: Order Not Found
    status: 404
    description: "The requested order does not exist or is not accessible to the caller"
  - type: order-validation-failed
    title: Order Validation Failed
    status: 422
    description: "The request body failed domain validation"
  - type: order-state-conflict
    title: Order State Conflict
    status: 409
    description: "The requested operation is not valid for the order's current status"
```

---

## Expected Output

### OpenAPI Spec (`docs/api/openapi.yaml`)

- All CRUD paths for `/api/v1/orders` and nested `/api/v1/orders/{orderId}/line-items`
- `POST /api/v1/orders/{orderId}/confirm` and `POST /api/v1/orders/{orderId}/cancel`
- `BearerAuth` security scheme with JWT format
- All three OAuth scopes declared
- Cursor-based pagination on `GET /api/v1/orders`
- RFC 9457 Problem Details schema for all 4xx/5xx responses
- Concrete request body example for `POST /api/v1/orders`

### Java Controller (`src/main/java/com/acme/orders/api/OrderController.java`)

```java
@RestController
@RequestMapping("/api/v1/orders")
@Tag(name = "Orders", description = "Order management endpoints")
public class OrderController {

    private final GetOrderUseCase getOrder;
    private final ListOrdersUseCase listOrders;
    private final CreateOrderUseCase createOrder;
    private final ConfirmOrderUseCase confirmOrder;
    private final CancelOrderUseCase cancelOrder;
    private final DeleteOrderUseCase deleteOrder;

    // constructor injection
    // all method stubs returning ResponseEntity<T> with explicit status codes
    // @Operation, @ApiResponse annotations on every method
}
```

### DTOs (Java records)

```java
public record CreateOrderRequest(
    @NotBlank @Size(max = 36) String customerId,
    @NotEmpty List<@Valid CreateOrderLineItemRequest> items,
    @NotBlank @Pattern(regexp = "^[A-Z]{3}$") String currency
) {}

public record OrderResponse(
    String id,
    String customerId,
    String status,
    MoneyResponse total,
    String createdAt,
    String updatedAt
) {}
```

### Use Case Stubs

```java
@Service
public class CreateOrderUseCase {
    private final IOrderRepository orders;
    private final IEventPublisher events;

    public CreateOrderUseCase(IOrderRepository orders, IEventPublisher events) { ... }

    public OrderResult execute(CreateOrderCommand command) {
        // TODO(PROJ-XXX): implement order creation
        throw new UnsupportedOperationException("Not yet implemented");
    }
}
```
