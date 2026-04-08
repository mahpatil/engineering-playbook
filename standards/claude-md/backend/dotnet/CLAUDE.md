# .NET Backend Standards

Read `../../CLAUDE.md` first. This file extends those principles for .NET services built with ASP.NET Core.

---

## Language & Runtime

- **.NET 8+** is the minimum. .NET 9 is preferred for new services.
- **C# 12+** language version. Enable nullable reference types and implicit usings in every project.
- Use modern C# features. Do not write C# 7-era code in new services.

```xml
<!-- Directory.Build.props — applies to all projects in the solution -->
<Project>
  <PropertyGroup>
    <TargetFramework>net9.0</TargetFramework>
    <LangVersion>latest</LangVersion>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <TreatWarningsAsErrors>true</TreatWarningsAsErrors>
    <AnalysisMode>AllEnabledByDefault</AnalysisMode>
  </PropertyGroup>
</Project>
```

### Use These C# Features

| Feature | When to use |
|---|---|
| Records | Immutable DTOs, CQRS commands/queries, value objects |
| Primary constructors | Services and repositories with simple DI (C# 12) |
| Required members | Force initialization of mandatory DTO properties |
| Pattern matching | Switch expressions over discriminated unions |
| `IAsyncEnumerable` | Streaming result sets from repositories |
| `Span<T>` / `Memory<T>` | High-performance parsing / serialization paths |
| `ValueTask<T>` | Async methods that frequently complete synchronously |
| Init-only setters | Immutable DTOs configured via object initializer |

```csharp
// GOOD — record for immutable command
public record CreateOrderCommand(
    string CustomerId,
    IReadOnlyList<OrderLineItem> Items,
    string Currency
);

// GOOD — result type as discriminated union
public abstract record OrderResult
{
    public sealed record Created(Order Order) : OrderResult;
    public sealed record Rejected(string Reason) : OrderResult;
}

// GOOD — pattern match on result
return result switch
{
    OrderResult.Created c   => CreatedAtRoute("GetOrder", new { id = c.Order.Id }, ToDto(c.Order)),
    OrderResult.Rejected r  => UnprocessableEntity(ProblemFor(r.Reason)),
    _                       => throw new UnreachableException()
};
```

### Avoid These

- `null` as a return value from public methods. Use `T?` with nullable reference types enabled, or a result/option type.
- Mutable DTOs with only setters — prefer `init` or records.
- `dynamic` type in production code.
- `Thread.Sleep` — use `Task.Delay` and `CancellationToken`.
- `async void` methods except for event handlers (use `async Task` everywhere else).
- `.Result` or `.Wait()` on `Task` — this causes deadlocks. Always `await`.

---

## Project Structure

Follow Clean Architecture with one project per layer:

```
Solution.sln
  src/
    Acme.Orders.Domain/           # Entities, value objects, domain events, domain services
    Acme.Orders.Application/      # Use cases, CQRS handlers, ports (interfaces)
    Acme.Orders.Infrastructure/   # EF Core, HTTP clients, messaging, persistence adapters
    Acme.Orders.Api/              # ASP.NET Core minimal API / controllers, request/response models
  tests/
    Acme.Orders.Domain.Tests/
    Acme.Orders.Application.Tests/
    Acme.Orders.Integration.Tests/
    Acme.Orders.Contract.Tests/
    Acme.Orders.E2E.Tests/
```

**Dependency rule (enforced by NDepend or ArchUnitNET):**
```
Api → Application → Domain
Infrastructure → Application → Domain
Infrastructure must NOT be referenced by Api directly (only via DI registration)
Domain has zero external dependencies
```

---

## ASP.NET Core Standards

### Minimal APIs vs Controllers

**Prefer Minimal APIs** for new services. They are lighter, align well with CQRS dispatch, and produce less boilerplate.

```csharp
// Program.cs — minimal API endpoint registration
app.MapPost("/api/v1/orders", async (
    CreateOrderCommand command,
    ISender mediator,
    CancellationToken ct) =>
{
    var result = await mediator.Send(command, ct);
    return result switch
    {
        OrderResult.Created c   => Results.CreatedAtRoute("GetOrder",
                                      new { id = c.Order.Id }, ToDto(c.Order)),
        OrderResult.Rejected r  => Results.UnprocessableEntity(ProblemFor(r.Reason)),
        _                       => throw new UnreachableException()
    };
})
.WithName("CreateOrder")
.WithTags("Orders")
.Produces<OrderDto>(201)
.ProducesValidationProblem()
.RequireAuthorization();
```

Use Controllers only when integrating with frameworks that require them (e.g. some legacy middleware, versioning libraries).

### Configuration

- Use `appsettings.yml` format where possible (install `NetEscapades.Configuration.Yaml`). If not, `appsettings.json` with strongly-typed options.
- **No secrets in `appsettings.json`** or committed config files. Use environment variables or the cloud secrets manager.
- Use the Options pattern (`IOptions<T>`, `IOptionsSnapshot<T>`) with validated POCO classes.

```csharp
public record PaymentsOptions
{
    public required string ProviderUrl { get; init; }
    public required int TimeoutSeconds { get; init; }
    public required int MaxRetries { get; init; }
}

// Registration with validation
builder.Services.AddOptions<PaymentsOptions>()
    .BindConfiguration("Payments")
    .ValidateDataAnnotations()
    .ValidateOnStart();
```

### Middleware Order

The correct middleware order in `Program.cs`:

```csharp
app.UseExceptionHandler();           // 1. Global error handling
app.UseHttpsRedirection();           // 2. Force HTTPS
app.UseCorrelationId();              // 3. Correlation ID (custom or library)
app.UseSerilogRequestLogging();      // 4. Request logging
app.UseAuthentication();             // 5. Who are you?
app.UseAuthorization();              // 6. What can you do?
app.UseRateLimiter();                // 7. Rate limiting
app.MapControllers();                // 8. Routing
```

---

## CQRS with MediatR

All application logic is dispatched through MediatR. Controllers and endpoints are thin orchestrators.

### Commands vs Queries

| | Command | Query |
|---|---|---|
| Intent | Mutate state | Read state |
| Returns | `Unit` or result type | DTO or collection |
| Validation | FluentValidation pipeline behaviour | FluentValidation |
| Caching | Never cached | May be cached |

```csharp
// Command
public record ConfirmOrderCommand(Guid OrderId, string TransactionId) : IRequest<OrderResult>;

public class ConfirmOrderHandler : IRequestHandler<ConfirmOrderCommand, OrderResult>
{
    private readonly IOrderRepository _orders;
    private readonly IEventPublisher _events;

    public ConfirmOrderHandler(IOrderRepository orders, IEventPublisher events)
        => (_orders, _events) = (orders, events);

    public async Task<OrderResult> Handle(ConfirmOrderCommand cmd, CancellationToken ct)
    {
        var order = await _orders.GetByIdAsync(cmd.OrderId, ct)
            ?? throw new EntityNotFoundException($"Order {cmd.OrderId} not found");

        var result = order.Confirm(new PaymentConfirmation(cmd.TransactionId));

        await _orders.SaveAsync(order, ct);
        await _events.PublishAsync(order.PullDomainEvents(), ct);

        return result;
    }
}
```

### Pipeline Behaviours

Register these behaviours in order:

1. `LoggingBehaviour<,>` — log command/query with correlation ID
2. `ValidationBehaviour<,>` — run FluentValidation; throw `ValidationException` on failure
3. `TransactionBehaviour<,>` — wrap commands in a DB transaction (queries excluded)
4. `CachingBehaviour<,>` — cache query results (for queries implementing `ICacheable`)

```csharp
builder.Services.AddMediatR(cfg =>
{
    cfg.RegisterServicesFromAssemblyContaining<Application.AssemblyMarker>();
    cfg.AddOpenBehavior(typeof(LoggingBehaviour<,>));
    cfg.AddOpenBehavior(typeof(ValidationBehaviour<,>));
    cfg.AddOpenBehavior(typeof(TransactionBehaviour<,>));
    cfg.AddOpenBehavior(typeof(CachingBehaviour<,>));
});
```

### Validation with FluentValidation

```csharp
public class CreateOrderCommandValidator : AbstractValidator<CreateOrderCommand>
{
    public CreateOrderCommandValidator()
    {
        RuleFor(x => x.CustomerId).NotEmpty().MaximumLength(36);
        RuleFor(x => x.Items).NotEmpty().WithMessage("An order must have at least one item");
        RuleForEach(x => x.Items).SetValidator(new OrderLineItemValidator());
        RuleFor(x => x.Currency).NotEmpty().Length(3).Matches("^[A-Z]{3}$");
    }
}
```

---

## Entity Framework Core

- **EF Core 8+**. Do not use EF6.
- Database migrations via `dotnet ef migrations`. Never use `EnsureCreated` in production.
- Use Code-First migrations. Migration files are committed to source control.
- Configure `QueryTrackingBehavior.NoTracking` globally for queries. Opt in to tracking for write operations.

```csharp
// DbContext configuration
protected override void OnConfiguring(DbContextOptionsBuilder options)
{
    options.UseQueryTrackingBehavior(QueryTrackingBehavior.NoTracking);
}

// EF entities live in Infrastructure, not Domain
internal class OrderEntity
{
    public Guid Id { get; set; }
    public string CustomerId { get; set; } = default!;
    public OrderStatus Status { get; set; }
    // ... persistence-optimised shape, maps to/from domain Order
}
```

- Map EF entities to domain objects at the repository boundary. Domain objects must not have navigation properties or `[Key]` annotations.
- Use `IQueryable` only in repository implementations — never expose `IQueryable` outside the infrastructure layer.
- Avoid lazy loading. Use explicit loading or eager loading with `Include`.

---

## Testing

### Unit Tests (xUnit)

```csharp
public class ConfirmOrderCommandHandlerTests
{
    private readonly Mock<IOrderRepository> _orders = new();
    private readonly Mock<IEventPublisher> _events = new();
    private readonly ConfirmOrderHandler _handler;

    public ConfirmOrderCommandHandlerTests()
        => _handler = new ConfirmOrderHandler(_orders.Object, _events.Object);

    [Fact]
    public async Task Handle_ShouldPublishOrderConfirmedEvent_WhenOrderIsPending()
    {
        var order = OrderBuilder.Pending().Build();
        _orders.Setup(r => r.GetByIdAsync(order.Id, default)).ReturnsAsync(order);

        await _handler.Handle(new ConfirmOrderCommand(order.Id, "txn-123"), default);

        _events.Verify(e => e.PublishAsync(
            It.Is<IEnumerable<IDomainEvent>>(events =>
                events.Any(ev => ev is OrderConfirmedEvent)), default));
    }
}
```

### Integration Tests (WebApplicationFactory + Testcontainers)

```csharp
public class OrdersApiTests : IClassFixture<WebApplicationFactory<Program>>, IAsyncLifetime
{
    private static readonly PostgreSqlContainer Postgres =
        new PostgreSqlBuilder().WithImage("postgres:16-alpine").Build();

    public async Task InitializeAsync() => await Postgres.StartAsync();
    public async Task DisposeAsync() => await Postgres.DisposeAsync();

    [Fact]
    public async Task POST_Orders_Returns201_WithValidPayload()
    {
        var factory = new WebApplicationFactory<Program>()
            .WithWebHostBuilder(host =>
                host.UseSetting("ConnectionStrings:Default", Postgres.GetConnectionString()));

        var client = factory.CreateClient();
        var response = await client.PostAsJsonAsync("/api/v1/orders", ValidCreateOrderRequest());

        response.StatusCode.Should().Be(HttpStatusCode.Created);
        response.Headers.Location.Should().NotBeNull();
    }
}
```

- Use **FluentAssertions** for readable assertions. Do not use raw `Assert.Equal`.
- Use **Bogus** for test data generation. Do not hardcode test data.
- Use **Respawn** to reset database state between tests.

### Contract Tests

- Use PactNet for consumer-driven contract tests.
- Provider verification runs in CI on every build.

---

## Structured Logging with Serilog

```csharp
// Program.cs
builder.Host.UseSerilog((ctx, cfg) => cfg
    .ReadFrom.Configuration(ctx.Configuration)
    .Enrich.FromLogContext()
    .Enrich.WithCorrelationId()
    .Enrich.WithMachineName()
    .WriteTo.Console(new JsonFormatter()));
```

```csharp
// Log structured events, not interpolated strings
Log.Information("Order confirmed {@OrderId} for {@CustomerId} amount {@Amount} {@Currency}",
    order.Id, order.CustomerId, order.Total.Amount, order.Total.Currency);

// BAD — loses structure, cannot be queried by field
Log.Information($"Order {order.Id} confirmed for customer {order.CustomerId}");
```

Configure minimum log levels in `appsettings.json`. `Debug` and below are off in production.

---

## Error Handling

### ProblemDetails

Use the built-in `IProblemDetailsService` (ASP.NET Core 7+) with a global exception handler:

```csharp
// Program.cs
builder.Services.AddProblemDetails(options =>
{
    options.CustomizeProblemDetails = ctx =>
    {
        ctx.ProblemDetails.Extensions["correlationId"] =
            ctx.HttpContext.TraceIdentifier;
        ctx.ProblemDetails.Extensions["service"] = "order-service";
    };
});

app.UseExceptionHandler();
```

```csharp
// Global exception handler
public class GlobalExceptionHandler : IExceptionHandler
{
    public async ValueTask<bool> TryHandleAsync(
        HttpContext ctx, Exception ex, CancellationToken ct)
    {
        var (status, title) = ex switch
        {
            EntityNotFoundException  => (404, "Not Found"),
            ValidationException      => (422, "Validation Failed"),
            UnauthorizedAccessException => (403, "Forbidden"),
            _                        => (500, "Internal Server Error")
        };

        await ctx.Response.WriteAsJsonAsync(new ProblemDetails
        {
            Status = status,
            Title = title,
            Detail = status < 500 ? ex.Message : "An unexpected error occurred",
        }, ct);
        return true;
    }
}
```

---

## Resilience with Microsoft.Extensions.Http.Resilience

Use the Resilience pipeline from .NET 8's `Microsoft.Extensions.Http.Resilience` (Polly v8 backed):

```csharp
builder.Services.AddHttpClient<IPaymentsClient, HttpPaymentsClient>(client =>
{
    client.BaseAddress = new Uri(paymentsOptions.ProviderUrl);
    client.Timeout = TimeSpan.FromSeconds(paymentsOptions.TimeoutSeconds);
})
.AddStandardResilienceHandler(options =>
{
    options.Retry.MaxRetryAttempts = 3;
    options.CircuitBreaker.SamplingDuration = TimeSpan.FromSeconds(10);
    options.CircuitBreaker.FailureRatio = 0.5;
    options.TotalRequestTimeout.Timeout = TimeSpan.FromSeconds(paymentsOptions.TimeoutSeconds);
});
```

---

## Observability

Use OpenTelemetry .NET SDK:

```csharp
builder.Services.AddOpenTelemetry()
    .WithTracing(tracing => tracing
        .AddAspNetCoreInstrumentation()
        .AddEntityFrameworkCoreInstrumentation()
        .AddHttpClientInstrumentation()
        .AddOtlpExporter())
    .WithMetrics(metrics => metrics
        .AddAspNetCoreInstrumentation()
        .AddRuntimeInstrumentation()
        .AddPrometheusExporter());
```

Add custom business metrics:

```csharp
public class OrderMetrics
{
    private readonly Counter<long> _ordersCreated;
    private readonly Histogram<double> _processingTime;

    public OrderMetrics(IMeterFactory meterFactory)
    {
        var meter = meterFactory.Create("Acme.Orders");
        _ordersCreated = meter.CreateCounter<long>("orders.created.total");
        _processingTime = meter.CreateHistogram<double>("orders.processing.duration",
            unit: "ms");
    }
}
```

---

## Security

- **Authentication**: Use `Microsoft.AspNetCore.Authentication.JwtBearer` for JWT validation. Configure authority and audience from configuration — never hardcode.
- **Authorization**: Use policy-based authorization (`[Authorize(Policy = "RequireOrdersWrite")]`). Do not use role strings directly in controllers.
- **HTTPS**: `UseHttpsRedirection` is mandatory. HSTS enabled in production.
- **CORS**: Configure explicitly. Never use `AllowAnyOrigin` in production.
- **Dependency scanning**: Use `dotnet list package --vulnerable` in CI. Block on critical CVEs.

---

## NuGet & Build Standards

```xml
<!-- Directory.Build.props — enforce across all projects -->
<Project>
  <PropertyGroup>
    <TreatWarningsAsErrors>true</TreatWarningsAsErrors>
    <Nullable>enable</Nullable>
    <EnforceCodeStyleInBuild>true</EnforceCodeStyleInBuild>
  </PropertyGroup>
  <ItemGroup>
    <!-- Roslyn analyzers applied everywhere -->
    <PackageReference Include="Microsoft.CodeAnalysis.NetAnalyzers" PrivateAssets="all" />
    <PackageReference Include="SonarAnalyzer.CSharp" PrivateAssets="all" />
  </ItemGroup>
</Project>
```

- Pin all NuGet versions in `Directory.Packages.props` (Central Package Management).
- Run `dotnet format` before every commit.
- SonarQube analysis runs in CI. Quality Gate failures block merges.

---

## Related Standards

- `../../CLAUDE.md` — Root engineering principles
- `../../api/CLAUDE.md` — API design, versioning, error shapes
- `standards/overall/tech-stack.md` — Approved .NET libraries
- `standards/detailed/microservices.md` — Microservice decomposition
