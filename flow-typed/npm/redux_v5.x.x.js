// flow-typed signature: redux_v5.0.1
// flow-typed version: v5.0.1/redux/flow_>=v0.104.x

declare module 'redux' {
  declare type State = any;
  declare type Action = {
    type: any,
    [key: string]: any,
  };
  declare type PreloadedState = any;
  declare type Reducer<S, A> = (state: ?S, action: A) => S;

  declare type Dispatch = (action: Action) => Action;

  declare type MiddlewareAPI = {
    dispatch: Dispatch,
    getState: () => State,
  };

  declare type Middleware =
    (api: MiddlewareAPI) =>
      (next: Dispatch) =>
        (action: Action) => any;

  declare type Store = {
    dispatch: Dispatch,
    getState: () => State,
    subscribe: (listener: () => void) => () => void,
    replaceReducer: (nextReducer: Reducer<any, Action>) => void,
  };

  declare type StoreCreator = (
    reducer: Reducer<any, Action>,
    preloadedState?: PreloadedState,
    enhancer?: StoreEnhancer
  ) => Store;

  declare type StoreEnhancer = (next: StoreCreator) => StoreCreator;

  declare type ActionCreator = (...args: any[]) => Action;
  declare type ActionCreatorsMapObject = { [key: string]: ActionCreator };

  declare class Redux {
    bindActionCreators(
      actionCreators: ActionCreatorsMapObject,
      dispatch: Dispatch
    ): ActionCreatorsMapObject;

    combineReducers(
      reducers: { [key: string]: Reducer<any, Action> }
    ): Reducer<any, Action>;

    createStore(
      reducer: Reducer<any, Action>,
      preloadedState?: PreloadedState,
      enhancer?: StoreEnhancer
    ): Store;

    applyMiddleware(
      ...middlewares: Array<Middleware>
    ): StoreEnhancer;

    compose(...funcs: Array<Function>): Function;
  }

  declare module.exports: Redux;
}
