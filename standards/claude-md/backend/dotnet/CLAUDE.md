# .NET Backend Standards

Extends ../../CLAUDE.md.

## Versions and libraries
| Area | Standard |
|---|---|
| Runtime | Latest LTS (.NET 10) for new services. .NET 8 is the minimum and leaves support in Nov 2026, so migrate remaining services |
| Language | C# `latest`, nullable and implicit usings on |
| API | Minimal APIs; controllers only where a library requires them |
| Data | EF Core (same major as the runtime), code-first migrations committed to source control |
| Mediator | MediatR is commercially licensed from v13; confirm licensing before adding it, otherwise use plain handler interfaces |
| Validation | FluentValidation |
| Logging | Serilog, JSON console formatter |
| Telemetry | OpenTelemetry .NET SDK (ASP.NET Core, HttpClient, EF Core, runtime instrumentation; OTLP exporter) |
| Resilience | `Microsoft.Extensions.Http.Resilience` (Polly v8) |
| Tests | xUnit, FluentAssertions, Bogus, Respawn, Testcontainers, WebApplicationFactory, PactNet |

- `dynamic`, `async void`, `.Result`/`.Wait()`, `Thread.Sleep` are banned (analyzers enforce).
- Result unions: `abstract record` with nested `sealed record` cases; `switch` ends in `UnreachableException`.

## Solution layout
```
src/Acme.<Svc>.{Domain,Application,Infrastructure,Api}
tests/Acme.<Svc>.{Domain,Application,Integration,Contract,E2E}.Tests
```
- `Api` references `Application` and, for DI registration only, `Infrastructure` (composition root). No other code in `Api` may use `Infrastructure` types.
- `Domain` has no package references. EF entities are `internal` in `Infrastructure` and mapped to domain objects at the repository; no `[Key]` or navigation properties in `Domain`.
- `IQueryable` never leaves `Infrastructure`.
- Enforced by NetArchTest or ArchUnitNET in `Architecture.Tests`, run in CI.

## Build enforcement
`Directory.Build.props`:
```xml
<PropertyGroup>
  <TargetFramework>net10.0</TargetFramework>
  <LangVersion>latest</LangVersion>
  <Nullable>enable</Nullable>
  <ImplicitUsings>enable</ImplicitUsings>
  <TreatWarningsAsErrors>true</TreatWarningsAsErrors>
  <AnalysisMode>AllEnabledByDefault</AnalysisMode>
  <EnforceCodeStyleInBuild>true</EnforceCodeStyleInBuild>
  <NuGetAudit>true</NuGetAudit>
  <NuGetAuditMode>all</NuGetAuditMode>
  <NuGetAuditLevel>high</NuGetAuditLevel>
</PropertyGroup>
<ItemGroup>
  <PackageReference Include="SonarAnalyzer.CSharp" PrivateAssets="all" />
</ItemGroup>
```
- `Directory.Packages.props` with `ManagePackageVersionsCentrally=true` pins every version.
- CI: `dotnet format --verify-no-changes`, `dotnet build -warnaserror`, SonarQube Quality Gate blocks merge. Vulnerable packages fail the build via NuGetAudit plus warnings-as-errors.
- Coverage (branch, 80%), via coverlet:
  `dotnet test /p:CollectCoverage=true /p:Threshold=80 /p:ThresholdType=branch /p:ThresholdStat=total`

## ASP.NET Core
- Options pattern with `required`/`init` records: `AddOptions<T>().BindConfiguration("Section").ValidateDataAnnotations().ValidateOnStart()`. Secrets only from env vars or the secrets manager; `appsettings*.json` carry none.
- Pipeline order is load-bearing:
```csharp
app.UseExceptionHandler();      // global errors first
app.UseHttpsRedirection();
app.UseHsts();                  // non-development only
app.UseCorrelationId();         // custom middleware or library
app.UseSerilogRequestLogging();
app.UseCors();
app.UseAuthentication();
app.UseAuthorization();
app.UseRateLimiter();
```
- Health endpoints, exposed externally exactly as below:
```csharp
app.MapHealthChecks("/health/live",  new() { Predicate = r => r.Tags.Contains("live") });
app.MapHealthChecks("/health/ready", new() { Predicate = r => r.Tags.Contains("ready") });
```
- JwtBearer authority and audience from configuration. Policy-based authorization (`RequireAuthorization("OrdersWrite")`), not role strings. CORS lists explicit origins; never `AllowAnyOrigin` in production.

## Handlers and pipeline (if MediatR is used)
Behavior order: Logging, Validation, Transaction (commands only), Caching (`ICacheable` queries).

## Exception to HTTP mapping
Register with `AddExceptionHandler<GlobalExceptionHandler>()` and `AddProblemDetails` (set `correlationId` and `service` in `CustomizeProblemDetails`; `traceId` is added by default).

| Exception | Status |
|---|---|
| `FluentValidation.ValidationException` | 422 (with `errors[{field,message}]`) |
| `BusinessRuleViolationException`, `DbUpdateConcurrencyException` | 409 |
| `EntityNotFoundException` | 404 |
| `ExternalServiceException` (HttpClient/broker failure) | 502 |
| anything else | 500 (generic detail; log the exception) |

`detail` carries the exception message only for status < 500.

## EF Core
- `NoTracking` by default (`UseQueryTrackingBehavior`); opt in to tracking on write paths. No lazy loading; use `Include` or projections.
- `EnsureCreated` only in tests; production migrations run as a pipeline step, not at startup.

## Resilience
`AddStandardResilienceHandler` on every typed `HttpClient`. It retries all methods by default, so call `options.Retry.DisableForUnsafeHttpMethods()` unless the request carries an idempotency key. Set `TotalRequestTimeout` from options.

## Tests
- Integration: `WebApplicationFactory<Program>` (make `Program` visible with `public partial class Program`) plus Testcontainers for the production database engine; Respawn between tests. Share one container per collection fixture, not per test.
