# Read the projects one step at a time

Start with Stockroom. Its task is close to your warehouse work, and its backend uses Java. You do not need to learn every file before you can understand one request.

Use this guide in short sessions. At the end of each session, close the guide and explain the task in your own words. If a part is unclear, mark that part and return to it. Memorizing the project description is not the same as being able to change the code.

## 1. Name the parts

| Part | Plain meaning | Where it appears |
| --- | --- | --- |
| HTML | The elements on a page, such as headings, inputs, and buttons | React creates these elements |
| CSS | Rules for spacing, color, type, and layout | `web/src/styles.css` |
| JavaScript | The language the browser runs | Built from the TypeScript files |
| TypeScript | JavaScript with checks on the kinds of values the code uses | `web/src/App.tsx` and `api.ts` |
| React | A library for building a page from components and state | Each app's `web/src` folder |
| Vite | The tool that runs the frontend during development and builds its files | `web/vite.config.ts` |
| Java | The backend language in Stockroom | `src/main/java` |
| Spring Boot | Starts and connects common parts of the Java web app | Stockroom's application, routes, and service |
| Python | The backend language in Import Desk and Source Notes | `app` |
| FastAPI | Maps HTTP requests to Python functions and validates request data | `app/main.py` |
| SQL | The language used to read and change database records | Strings in the backend and `schema.sql` |
| PostgreSQL | The database program storing those records | The database service |
| pgvector | Adds vector storage and comparison to PostgreSQL | Source Notes only |
| Docker | Packages an app with the tools it needs to run | `Dockerfile` |
| GitHub Actions | Runs setup, builds, and tests after code is pushed | `.github/workflows/check.yml` |

Next.js belongs to FiberScout. These three new apps use React with Vite. React and TypeScript are not interchangeable names: React builds the interface, and TypeScript checks the code that builds it.

## 2. Follow one click in Stockroom

Open the app as `worker`. Look at an order before clicking anything. Identify its customer, product, requested quantity, picked quantity, and status.

Imagine an order needs 12 boxes, and the shelf has 8. Predict the result of **Pick available stock**: eight picked, four still missing, zero left on the shelf, and a shortage state.

The browser sends a request like this. The ID and values are examples, not a command to run against your saved records:

```http
POST /api/orders/2/pick
Content-Type: application/json

{"version": 0, "key": "one-request-id"}
```

`POST` means the request asks the server to perform an action. The path identifies the order and the action. The JSON body carries the version the page saw and a key for this one request. The request also carries the session cookie and CSRF token.

The page does not send a new shelf count and ask the database to trust it. The server reads the available stock and calculates the amount itself.

Open these files in this order:

1. `web/src/App.tsx`: find the button text and the request it makes.
2. `web/src/api.ts`: find the request headers and error handling.
3. `src/main/java/com/jaryn/stockroom/Api.java`: find `@PostMapping("/orders/{id}/pick")`.
4. `src/main/java/com/jaryn/stockroom/StockService.java`: find `move`.
5. `src/main/resources/schema.sql`: find `products` and `order_items`.

The Java route is short because it hands the work to the service. `@PathVariable` reads the order ID from the URL. `@RequestBody` reads the JSON body. `@Valid` applies the validation rules on the request record. `Authentication` gives the signed-in account.

This is the main calculation inside the service:

```java
int remaining = requested - alreadyPicked;
int taken = Math.min(remaining, available);
```

The example uses shorter names than the actual code. `Math.min` chooses the smaller number. It prevents a pick from taking more than the order needs or more than the shelf holds.

Try explaining this without looking: “The button asks the Java server to pick an order. The server checks the request, reads the stock, picks only what is available, and sends the updated order back.”

## 3. Read the SQL slowly

A table is a collection of rows. Each row describes one record. A column describes one kind of value in that record.

For example, a product row has a SKU, name, aisle, shelf count, and version. The SKU identifies that product. An order can contain several products, so `order_items` connects order IDs to product SKUs.

```sql
SELECT sku, name, on_hand
FROM products
WHERE on_hand < 10
ORDER BY name;
```

Read it as four small instructions: choose these columns; read the products table; keep rows with fewer than ten boxes; sort by name.

```sql
SELECT i.quantity, i.picked, p.name
FROM order_items i
JOIN products p ON p.sku = i.sku
WHERE i.order_id = 2;
```

`i` and `p` are short names for the tables. `JOIN` connects rows whose SKU matches. The order line supplies requested and picked quantities; the product row supplies its name. The query does not copy the product name into every order line.

A primary key identifies a row, such as the product SKU. A foreign key links one table to another, such as an order line's SKU pointing to `products`. A constraint is a rule the database enforces. `CHECK (on_hand >= 0)` rejects negative shelf counts even if application code makes a mistake.

The Java code uses `?` as a slot for a value:

```java
db.update("UPDATE products SET on_hand=on_hand-? WHERE sku=?", taken, sku);
```

The SQL command and its values travel separately. The user's text is treated as a value rather than becoming part of the SQL command.

You can study these queries without running a write. When practicing edits, use a test database and know which database you are connected to.

## 4. Understand the three checks that protect stock

These solve different problems:

| Check | Problem | Example |
| --- | --- | --- |
| Request key | The same request arrives twice | A repeated pick must not remove eight more boxes |
| Version | A page has old information | Another tab changed the order after this page loaded |
| Row lock | Two actions reach the same stock at once | Two different orders both need the last five boxes |

A transaction keeps several database changes together. Stockroom reduces shelf stock, increases the picked quantity, changes the order state, and adds an activity entry. If one of those steps fails, the transaction rolls back. That prevents a shelf count from changing without the pick list changing too.

`@Transactional` tells Spring to run the method as one transaction. `SELECT ... FOR UPDATE` locks a row while the transaction works. Other writers must wait for that row. Products are locked in SKU order so two requests are less likely to wait on each other in opposite orders.

For approvals, the server also checks the account's role. Hiding a button on the worker screen helps the user, but it does not secure the route. Someone could send a request directly. The backend must still reject it.

Practice question: an order needs four boxes, and another order also needs four. The shelf holds five. What should happen if both picks run at once? One can get four and the other one. The shelf must end at zero, never at minus three.

## 5. Read a test as a short story

Open `integration/test_workflows.py` in Stockroom. Find `test_two_orders_cannot_overdraw_stock`.

The test sets up a product with five boxes and two orders asking for four each. It starts both pick requests and then checks the results: one ready order, one shortage order, five total picked boxes, and zero left on the shelf.

The setup, action, and checks are the three parts of the story. An `assert` says what must be true. A failed assertion means the observed behavior did not match the expectation.

This is an integration test because it sends real HTTP requests to the running Java app and checks a real PostgreSQL database. It is different from a small unit test of one function. It is also different from clicking through the screen in a browser. The project uses both automated checks and manual screen checks for different reasons.

GitHub Actions runs the checks on a separate Ubuntu machine. A green run records what passed for one commit. A workflow file by itself is only a set of instructions; the completed run is the evidence.

## 6. Move to Import Desk

Start with the sample import report. Match each rejected row to its reason. Then open `app/importer.py` and find `clean`.

The function checks required IDs, dates with time zones, and numeric limits. It uses `Decimal` for values such as fuel gallons. A missing value, `NaN`, a negative distance, or too many decimal places is rejected.

The API first saves a job. A separate worker later claims it. That means closing the browser does not stop the import. The dashboard reads job status; it does not perform the background work itself.

Follow these names: `enqueue`, `run_once`, `clean`, and `tick` in `app/worker.py`.

There are two duplicate checks. A file hash recognizes identical file contents. A reading ID recognizes a record inside a file. The same reading ID with different values is rejected so it does not silently replace an earlier reading.

A bad row value can be recorded while good rows are accepted. A structurally broken CSV fails the file and rolls back the import. Be able to explain that difference using the sample rejection report and the malformed-file test.

The worker uses a lease to recover a job whose earlier worker disappeared. It also checks the attempt number before writing, so an old attempt cannot finish over a newer attempt.

An index is a lookup structure that can help the database find matching rows. It costs storage and adds work when records change. Import Desk's benchmark measures one query before and after an index. Its local timing is evidence for that particular case, not a promise that every query will improve by the same amount.

## 7. Move to Source Notes

Load the sample guides. Ask who approves a stock adjustment, then open the source. Ask about dental insurance next. There is no answer to that second question in the sample guides.

Read `app/retrieval.py` in this order: `split_passages`, `vector`, `retrieve`, `local_quotes`, `validate_quotes`.

A passage is a small part of a document. It keeps the original line numbers. A vector is a list of numbers used for comparison. This app hashes words into 256 values. That is a repeatable word-matching method, not a trained language model.

Retrieval finds passages to consider. Quote selection chooses words from those passages. Validation checks that the quoted words really exist in the cited passage. These are separate jobs.

The optional API adapter can ask a model to select quotes. The model has no tool that approves notes or changes business records. The server still validates its returned quotes. Tests use controlled HTTP responses, so passing them does not mean the live model has been evaluated.

An exact quote can still fail to answer the question. A passage might share a few words while discussing a different topic. That is why the app keeps source links and a separate review step.

The eight-question check is a small regression set. It helps catch changes that break the supplied examples. It does not prove broad language understanding or complete protection against misleading instructions in documents.

## 8. Make one small change yourself

Pick one exercise at a time. Read the related code, predict what will change, make the edit, and check the result.

1. **React:** change a field label in Stockroom. Find which component owns it, rebuild the web app, and check the page.
2. **Java:** trace the rule that blocks loading an unfinished order. Explain why the backend must enforce it even if the button is hidden.
3. **SQL:** write a read-only query listing products with fewer than five boxes. Predict the rows before running it.
4. **Python:** choose one invalid CSV value and find the test that covers it. Explain why the value is invalid.
5. **Retrieval:** paraphrase a sample question. Record whether local search finds the same passage and why a word-based method might struggle.

Keep a short note for each exercise: what you changed, what you expected, what happened, and what you learned. Those notes give you specific examples for interviews.

## Explain the work honestly

The projects were built with LLM help for implementation, tests, documentation, and explanations. They are personal projects with sample data. The code and checks are available to inspect, and the backends run locally.

For an interview, choose one workflow you can explain and one detail you changed yourself. It is fine to say you used help and then explain what you understand. Do not claim production users, a live model evaluation, or independent mastery you have not developed yet.

Before using a bullet in an interview, check that you can answer: Where is the code? What can go wrong? Which check catches it? What would you change next?
