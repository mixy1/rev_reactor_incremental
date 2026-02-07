# Project Structure

```
documentation/
  plans/
  knowledge-base/

decompilation/
  build/
  tools/
  env/
  recovered/
  outputs/
  tmp/

implementation/
```

## Notes
- `decompilation/build/` contains original build artifacts and derived wasm binaries.
- `decompilation/recovered/` contains extracted assets, metadata, and scene maps.
- `implementation/` will host the Python + raylib reimplementation.
